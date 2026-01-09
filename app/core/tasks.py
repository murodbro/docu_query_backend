import os
from datetime import datetime

from app.core.hybrid_retriever import HybridRetriever
from app.core.reranker import CohereReranker
from app.core.schemas import TaskStatus, task_statuses
from app.ingest.chunker import chunk_documents
from app.ingest.index import index_manager
from app.ingest.loaders import load_document

_hybrid_retriever = None
_reranker = None


def get_hybrid_retriever() -> HybridRetriever:
    """Get or create hybrid retriever instance."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever


def get_reranker() -> CohereReranker:
    """Get or create reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = CohereReranker()
    return _reranker


def process_and_index_document(file_path: str, task_id: str):
    """Process document and create embeddings in background."""
    try:
        documents = load_document(file_path)
        nodes = chunk_documents(documents)

        index_manager.add_documents(nodes)
        get_hybrid_retriever().add_nodes(nodes)

        page_count = (
            documents[0].metadata.get(
                "total_pages",
                len(documents),
            )
            if documents
            else 0
        )

        task_statuses[task_id] = {
            "ok": True,
            "status": TaskStatus.COMPLETED,
            "filename": os.path.basename(file_path),
            "created_at": task_statuses.get(task_id, {}).get("created_at"),
            "completed_at": datetime.now().isoformat(),
            "chunks": len(nodes),
            "pages": page_count,
        }
    except Exception as e:
        task_statuses[task_id] = {
            "ok": False,
            "status": TaskStatus.FAILED,
            "filename": os.path.basename(file_path),
            "created_at": task_statuses.get(task_id, {}).get("created_at"),
            "failed_at": datetime.now().isoformat(),
            "error": str(e),
        }
