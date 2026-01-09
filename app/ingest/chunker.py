import re
from typing import List

from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from llama_index.core import Document
from llama_index.core.schema import BaseNode, TextNode

from app.config import settings


def normalize_text(text: str) -> str:
    """
    Clean text by removing visual separators, extra whitespace,
    and redundant special characters to improve embedding quality.
    """
    if not text:
        return ""

    text = re.sub(r"([=\-_*]){3,}", " ", text)
    text = re.sub(r"[\n\r\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


def chunk_documents(documents: List[Document]) -> List[BaseNode]:
    """Chunk documents with metadata preservation using semantic chunking."""
    text_splitter = SemanticChunker(
        OpenAIEmbeddings(api_key=settings.openai_api_key),
        breakpoint_threshold_type="percentile",  # "standard_deviation", "interquartile"
    )

    nodes = []
    char_position_map = {}

    for doc in documents:
        text = normalize_text(doc.get_content())
        doc_metadata = doc.metadata.copy() if doc.metadata else {}

        langchain_docs = text_splitter.create_documents([text])

        for langchain_doc in langchain_docs:
            node_metadata = doc_metadata.copy()
            if langchain_doc.metadata:
                node_metadata.update(langchain_doc.metadata)

            node = TextNode(
                text=langchain_doc.page_content,
                metadata=node_metadata,
            )

            if not node.metadata:
                node.metadata = {}

            if "file_name" not in node.metadata:
                node.metadata["file_name"] = doc_metadata.get("file_name", "unknown")

            doc_name = node.metadata.get("file_name", "unknown")

            if (
                "start_char_idx" not in node.metadata
                or node.metadata["start_char_idx"] is None
            ):
                if doc_name not in char_position_map:
                    char_position_map[doc_name] = 0
                node.metadata["start_char_idx"] = char_position_map[doc_name]

            chunk_length = len(node.get_content())
            char_position_map[doc_name] = node.metadata["start_char_idx"] + chunk_length

            nodes.append(node)

    return nodes
