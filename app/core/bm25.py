from typing import List, Tuple

from llama_index.core.schema import BaseNode
from rank_bm25 import BM25Okapi


class BM25Retriever:
    """BM25 keyword-based retriever."""

    def __init__(self, nodes: List[BaseNode]):
        """Initialize BM25 index from nodes."""
        self.nodes = nodes
        self.node_texts = [node.get_content() for node in nodes]
        tokenized_corpus = [text.lower().split() for text in self.node_texts]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 20) -> List[Tuple[BaseNode, float]]:
        """Search for top-k nodes matching the query."""
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        scored_nodes = list(zip(self.nodes, scores))
        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        return scored_nodes[:top_k]

    def add_nodes(self, nodes: List[BaseNode]) -> None:
        """Add new nodes to the BM25 index."""
        new_texts = [node.get_content() for node in nodes]

        self.nodes.extend(nodes)
        self.node_texts.extend(new_texts)

        all_tokenized = [text.lower().split() for text in self.node_texts]
        self.bm25 = BM25Okapi(all_tokenized)
