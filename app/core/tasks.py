from app.core.hybrid_retriever import HybridRetriever
from app.core.reranker import CohereReranker
from app.core.task_store import complete_task, fail_task
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


def process_and_index_document(
    file_path: str,
    task_id: str,
    folder_id: str = None,
    document_id: str = None,
    original_filename: str = None,
):
    """Process document and create embeddings in background."""
    try:
        documents = load_document(file_path)
        nodes = chunk_documents(documents)

        # Add folder_id, document_id, and override file_name with original filename
        for node in nodes:
            if folder_id:
                node.metadata["folder_id"] = str(folder_id)
            if document_id:
                node.metadata["document_id"] = str(document_id)
            # Override UUID-based filename with original user-facing filename
            if original_filename:
                node.metadata["file_name"] = original_filename

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

        complete_task(task_id, chunks=len(nodes), pages=page_count)
    except Exception as e:
        fail_task(task_id, error=str(e))
