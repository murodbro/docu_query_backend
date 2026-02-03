import re
from typing import Dict, List, Optional

from llama_index.core.schema import NodeWithScore


def _extract_key_sentences(text: str, query: str = None, max_length: int = 200) -> str:
    """Extract key sentences from chunk text for citation display."""
    if len(text) <= max_length:
        return text

    # Split into sentences
    sentences = re.split(r"[.!?]+\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return text[:max_length] + "..."

    # If query provided, prioritize sentences containing query keywords
    if query:
        query_words = set(query.lower().split())
        scored_sentences = []
        for sent in sentences:
            score = sum(1 for word in query_words if word in sent.lower())
            scored_sentences.append((score, sent))
        scored_sentences.sort(reverse=True, key=lambda x: x[0])
        sentences = [s for _, s in scored_sentences]

    # Build summary from sentences
    summary = ""
    for sent in sentences:
        if len(summary) + len(sent) + 2 <= max_length:
            if summary:
                summary += ". "
            summary += sent
        else:
            break

    if summary:
        return summary + "..." if len(text) > max_length else summary

    return text[:max_length] + "..."


def _estimate_page_number(node, metadata: Dict) -> int:
    """Estimate page number for documents without explicit page numbers."""
    page = metadata.get("page_number")

    if page is not None:
        return page

    start_char_idx = metadata.get("start_char_idx", 0)
    if start_char_idx is not None and start_char_idx > 0:
        estimated_page = (start_char_idx // 3000) + 1
        return estimated_page

    return None


def extract_citations(
    retrieved_nodes: List[NodeWithScore], query: Optional[str] = None
) -> List[Dict]:
    """Extract citation information from retrieved nodes with summarized text."""
    citations = []

    for node_score in retrieved_nodes:
        node = node_score.node
        metadata = node.metadata or {}
        chunk_text = node.get_content()

        page = _estimate_page_number(node, metadata)

        citation = {
            "document": metadata.get("file_name", "unknown"),
            "document_id": metadata.get("document_id"),
            "page": page,
            "chunk_text": _extract_key_sentences(chunk_text, query),
            "relevance_score": round(float(node_score.score), 4),
        }

        citations.append(citation)

    return citations
