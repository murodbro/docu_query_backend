from typing import List

import cohere
from llama_index.core.schema import NodeWithScore

from app.config import settings


class CohereReranker:
    """Cohere reranker for improving retrieval relevance."""

    def __init__(self):
        self.client = None
        if settings.cohere_api_key:
            try:
                self.client = cohere.Client(api_key=settings.cohere_api_key)
            except Exception:
                self.client = None

    def rerank(
        self, query: str, nodes: List[NodeWithScore], top_k: int = None
    ) -> List[NodeWithScore]:
        """Rerank nodes using Cohere API."""
        if top_k is None:
            top_k = settings.rerank_top_k

        if not nodes:
            return []

        if len(nodes) <= top_k:
            return nodes

        if not self.client:
            return nodes[:top_k]

        documents = [node.node.get_content() for node in nodes]

        try:
            response = self.client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=documents,
                top_n=top_k,
            )

            reranked_nodes = []
            for result in response.results:
                idx = result.index
                reranked_nodes.append(
                    NodeWithScore(
                        node=nodes[idx].node,
                        score=result.relevance_score,
                    )
                )

            return reranked_nodes
        except Exception:
            return nodes[:top_k]
