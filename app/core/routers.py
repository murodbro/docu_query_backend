import os
import uuid
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, Depends, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.citations import extract_citations
from app.core.database import get_db
from app.core.llm import generate_answer
from app.core.memory import memory
from app.core.schemas import QueryRequest, QueryResponse
from app.core.task_store import create_task, get_task as get_task_from_db
from app.core.tasks import (
    get_hybrid_retriever,
    get_reranker,
    process_and_index_document,
)
from app.auth.auth import get_current_user
from app.auth.models import User, Folder, Document, DocumentStatus

logger = logging.getLogger("docuquery")

router = APIRouter(prefix="/api")

# Daily upload limit per user (limit on folders/upload sessions, not files)
DAILY_UPLOAD_LIMIT = 3


def get_user_folders_today(db: Session, user_id: str) -> int:
    """Count how many folders (upload sessions) user created today."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = (
        db.query(Folder).filter(Folder.user_id == user_id, Folder.created_at >= today_start).count()
    )
    return count


def get_next_folder_name(db: Session, user_id: str) -> str:
    """Generate next folder name like 'Upload 1', 'Upload 2', etc."""
    count = db.query(Folder).filter(Folder.user_id == user_id).count()
    return f"Upload {count + 1}"


@router.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    folder_name: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload multiple files in one session (requires authentication)."""
    # Check daily folder limit
    folders_today = get_user_folders_today(db, current_user.id)
    if folders_today >= DAILY_UPLOAD_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily upload limit reached ({DAILY_UPLOAD_LIMIT} uploads). Try again tomorrow.",
        )

    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")

    # Create folder for this upload session
    folder = Folder(
        user_id=current_user.id,
        name=folder_name
        if folder_name and folder_name.strip()
        else get_next_folder_name(db, current_user.id),
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)

    # Create user-specific upload directory
    user_upload_dir = f"uploads/{current_user.id}/{folder.id}"
    os.makedirs(user_upload_dir, exist_ok=True)

    uploaded_docs = []

    for file in files:
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        save_path = f"{user_upload_dir}/{unique_filename}"
        task_id = str(uuid.uuid4())

        try:
            with open(save_path, "wb") as f:
                content = await file.read()
                f.write(content)

            # Create task in task store
            create_task(task_id, file.filename)

            # Create document record
            document = Document(
                folder_id=folder.id,
                filename=file.filename,
                file_path=save_path,
                status=DocumentStatus.PROCESSING,
                task_id=task_id,
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            # Start background indexing with folder_id and original filename
            background_tasks.add_task(
                process_and_index_document_with_status,
                save_path,
                task_id,
                document.id,
                folder.id,
                file.filename,
            )

            uploaded_docs.append(
                {
                    "id": document.id,
                    "filename": file.filename,
                    "task_id": task_id,
                    "status": "processing",
                }
            )
        except Exception as e:
            uploaded_docs.append(
                {
                    "filename": file.filename,
                    "status": "failed",
                    "error": str(e),
                }
            )

    return {
        "ok": True,
        "folder_id": folder.id,
        "folder_name": folder.name,
        "documents": uploaded_docs,
        "uploads_remaining": DAILY_UPLOAD_LIMIT - folders_today - 1,
    }


def process_and_index_document_with_status(
    file_path: str, task_id: str, document_id: str, folder_id: str, original_filename: str = None
):
    """Process document and update status in database."""
    from app.core.database import SessionLocal

    try:
        # This calls the existing indexing function with folder_id and original filename
        process_and_index_document(file_path, task_id, folder_id, document_id, original_filename)

        # Create new session for status update
        db = SessionLocal()
        try:
            # Update document status based on task status
            task = get_task_from_db(task_id)
            if task and task.get("status") == "completed":
                db.query(Document).filter(Document.id == document_id).update(
                    {"status": DocumentStatus.COMPLETED}
                )
            else:
                db.query(Document).filter(Document.id == document_id).update(
                    {"status": DocumentStatus.FAILED}
                )
            db.commit()
        finally:
            db.close()
    except Exception:
        db = SessionLocal()
        try:
            db.query(Document).filter(Document.id == document_id).update(
                {"status": DocumentStatus.FAILED}
            )
            db.commit()
        finally:
            db.close()


@router.get("/folders")
async def get_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all folders with their documents for the current user."""
    folders = (
        db.query(Folder)
        .filter(Folder.user_id == current_user.id)
        .order_by(Folder.created_at.desc())
        .all()
    )

    # Get remaining uploads for today
    folders_today = get_user_folders_today(db, current_user.id)

    return {
        "folders": [
            {
                "id": folder.id,
                "name": folder.name,
                "created_at": folder.created_at.isoformat(),
                "documents": [
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "status": doc.status,
                        "created_at": doc.created_at.isoformat(),
                    }
                    for doc in folder.documents
                ],
            }
            for folder in folders
        ],
        "uploads_today": folders_today,
        "uploads_remaining": DAILY_UPLOAD_LIMIT - folders_today,
        "daily_limit": DAILY_UPLOAD_LIMIT,
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get the status of an indexing task."""
    task = get_task_from_db(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return task


@router.get("/documents/{document_id}/content")
async def get_document_content(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the content of a specific document for preview."""
    # Find document and verify ownership via folder
    document = (
        db.query(Document)
        .join(Folder)
        .filter(Document.id == document_id)
        .filter(Folder.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    try:
        # Try to read as text first
        with open(document.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "filename": document.filename, "type": "text"}
    except UnicodeDecodeError:
        # If text read fails, it might be binary (PDF, etc).
        return {
            "content": "Binary file preview not supported yet.",
            "filename": document.filename,
            "type": "binary",
        }
    except Exception as e:
        logger.error(f"Error reading file {document.id}: {e}")
        raise HTTPException(status_code=500, detail="Error reading file content")


@router.get("/documents/{document_id}/raw")
async def get_document_raw(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the raw file stream for a specific document."""
    # Find document and verify ownership
    document = (
        db.query(Document)
        .join(Folder)
        .filter(Document.id == document_id)
        .filter(Folder.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    # Return file response
    return FileResponse(document.file_path, filename=document.filename)


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the document knowledge base."""
    session_id = request.session_id or str(uuid.uuid4())

    try:
        retrieved_nodes = get_hybrid_retriever().retrieve(request.query)

        # Filter by folder_id if specified
        if request.folder_id:
            retrieved_nodes = [
                node
                for node in retrieved_nodes
                if str(node.metadata.get("folder_id", "")) == str(request.folder_id)
            ]

        if not retrieved_nodes:
            return QueryResponse(
                answer="I couldn't find any relevant information in the selected folder's documents.",
                sources=[],
                session_id=session_id,
            )

        reranked_nodes = get_reranker().rerank(request.query, retrieved_nodes)

        # Filter by relevance threshold
        RELEVANCE_THRESHOLD = 0.05
        reranked_nodes = [node for node in reranked_nodes if node.score >= RELEVANCE_THRESHOLD]

        if not reranked_nodes:
            return QueryResponse(
                answer="I couldn't find any sufficiently relevant information in the documents to answer your question.",
                sources=[],
                session_id=session_id,
            )

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
