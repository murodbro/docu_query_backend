import os
from typing import List, Optional

import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import BaseNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.config import settings


class IndexManager:
    """Singleton manager for the vector index."""

    _instance: Optional["IndexManager"] = None
    _index: Optional[VectorStoreIndex] = None
    _client: Optional[chromadb.Client] = None
    _collection: Optional[chromadb.Collection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self) -> VectorStoreIndex:
        """Initialize or load the index."""
        if self._index is not None:
            return self._index

        os.makedirs(settings.chroma_db_path, exist_ok=True)

        self._client = chromadb.PersistentClient(path=settings.chroma_db_path)

        try:
            self._collection = self._client.get_collection("docuquery")
        except Exception:
            self._collection = self._client.create_collection("docuquery")

        embed_model = OpenAIEmbedding(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

        vector_store = ChromaVectorStore(chroma_collection=self._collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        self._index = VectorStoreIndex(
            nodes=[],
            storage_context=storage_context,
            embed_model=embed_model,
        )

        return self._index

    def add_documents(self, nodes: List[BaseNode]) -> None:
        """Add documents to the existing index."""
        if self._index is None:
            self.initialize()

        for node in nodes:
            self._index.insert(node)

    def get_index(self) -> VectorStoreIndex:
        """Get the current index instance."""
        if self._index is None:
            self.initialize()
        return self._index

    def reset(self) -> None:
        """Reset the index (for testing)."""
        if self._client is not None:
            try:
                self._client.delete_collection("docuquery")
            except Exception:
                pass

        self._index = None
        self._collection = None
        self._client = None


index_manager = IndexManager()
