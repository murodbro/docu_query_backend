import os
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from app.core.citations import extract_citations
from app.core.llm import generate_answer
from app.core.memory import memory
from app.core.schemas import QueryRequest, QueryResponse, TaskStatus, task_statuses
from app.core.tasks import (
    get_hybrid_retriever,
    get_reranker,
    process_and_index_document,
)

router = APIRouter(prefix="/api")


@router.post("/upload")
async def upload(file: UploadFile, background_tasks: BackgroundTasks):
    """Upload and index a document."""
    os.makedirs("uploads", exist_ok=True)

    save_path = f"uploads/{file.filename}"
    task_id = str(uuid.uuid4())

    try:
        with open(save_path, "wb") as f:
            content = await file.read()
            f.write(content)

        task_statuses[task_id] = {
            "status": TaskStatus.PROCESSING,
            "filename": file.filename,
            "created_at": datetime.now().isoformat(),
        }

        background_tasks.add_task(process_and_index_document, save_path, task_id)

        return {
            "ok": True,
            "filename": file.filename,
            "task_id": task_id,
            "status": TaskStatus.PROCESSING,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get the status of an indexing task."""
    if task_id not in task_statuses:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return task_statuses[task_id]


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the document knowledge base."""
    session_id = request.session_id or str(uuid.uuid4())

    try:
        retrieved_nodes = get_hybrid_retriever().retrieve(request.query)

        if not retrieved_nodes:
            return QueryResponse(
                answer="I couldn't find any relevant information in the uploaded documents.",
                sources=[],
                session_id=session_id,
            )

        reranked_nodes = get_reranker().rerank(request.query, retrieved_nodes)

        conversation_history = memory.format_history_for_llm(session_id)

        answer = generate_answer(
            request.query,
            reranked_nodes,
            conversation_history if conversation_history else None,
        )

        citations = extract_citations(reranked_nodes, request.query)

        memory.add_message(session_id, "user", request.query)
        memory.add_message(session_id, "assistant", answer, {"sources": citations})

        return QueryResponse(
            answer=answer,
            sources=citations,
            session_id=session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_history(session_id: str):
    """Get conversation history for a session."""
    history = memory.get_history(session_id)
    return {"session_id": session_id, "history": history}
