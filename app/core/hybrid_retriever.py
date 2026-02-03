from typing import Dict, List, Tuple

from llama_index.core import QueryBundle, VectorStoreIndex
from llama_index.core.schema import BaseNode, NodeWithScore

from app.config import settings
from app.core.bm25 import BM25Retriever
from app.ingest.index import index_manager


class HybridRetriever:
    """Hybrid retriever combining vector and BM25 search."""

    def __init__(self):
        self.vector_index: VectorStoreIndex = index_manager.get_index()
        self.bm25_retriever: BM25Retriever = None
        self.all_nodes: List[BaseNode] = []
        self._load_nodes_from_index()

    def _load_nodes_from_index(self) -> None:
        """Load nodes from vector store for BM25 indexing."""
        try:
            docstore = self.vector_index.storage_context.docstore
            if hasattr(docstore, "docs"):
                nodes = [node for node in docstore.docs.values() if isinstance(node, BaseNode)]
                self.all_nodes = nodes
                if self.all_nodes:
                    self.bm25_retriever = BM25Retriever(self.all_nodes)
        except Exception:
            self.all_nodes = []
            self.bm25_retriever = None

    def add_nodes(self, nodes: List[BaseNode]) -> None:
        """Add nodes and update both indices."""
        self.all_nodes.extend(nodes)
        if self.bm25_retriever is None:
            self.bm25_retriever = BM25Retriever(self.all_nodes)
        else:
            self.bm25_retriever.add_nodes(nodes)

    def retrieve(self, query: str, top_k: int = None) -> List[NodeWithScore]:
        """Retrieve nodes using hybrid search."""
        if top_k is None:
            top_k = settings.top_k

        self._load_nodes_from_index()

        results: Dict[str, Tuple[BaseNode, float]] = {}

        vector_weight = settings.hybrid_search_weight
        bm25_weight = 1.0 - vector_weight

        if self.bm25_retriever:
            bm25_results = self.bm25_retriever.search(query, top_k=top_k * 2)
            max_bm25_score = max([score for _, score in bm25_results], default=1.0)

            for node, score in bm25_results:
                node_id = node.node_id if hasattr(node, "node_id") else str(id(node))
                normalized_score = score / max_bm25_score if max_bm25_score > 0 else 0.0
                if node_id not in results:
                    results[node_id] = (node, 0.0)
                _, current_score = results[node_id]
                results[node_id] = (
                    node,
                    current_score + bm25_weight * normalized_score,
                )

        try:
            query_bundle = QueryBundle(query_str=query)
            # Use as_retriever() to properly query the vector store
            retriever = self.vector_index.as_retriever(similarity_top_k=top_k * 2)
            vector_results = retriever.retrieve(query_bundle)
            max_vector_score = max([r.score for r in vector_results], default=1.0)

            for result in vector_results[: top_k * 2]:
                node_id = (
                    result.node.node_id if hasattr(result.node, "node_id") else str(id(result.node))
                )
                normalized_score = result.score / max_vector_score if max_vector_score > 0 else 0.0
                if node_id not in results:
                    results[node_id] = (result.node, 0.0)
                _, current_score = results[node_id]
                results[node_id] = (
                    result.node,
                    current_score + vector_weight * normalized_score,
                )
        except Exception as e:
            print(f"[ERROR] Vector retrieval failed: {e}")

        scored_nodes = sorted(results.values(), key=lambda x: x[1], reverse=True)

        return [NodeWithScore(node=node, score=score) for node, score in scored_nodes[:top_k]]
