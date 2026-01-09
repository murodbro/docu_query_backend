import os
from pathlib import Path
from typing import List

from llama_index.core import Document, SimpleDirectoryReader
from llama_index.readers.file import DocxReader, PDFReader


def load_document(file_path: str) -> List[Document]:
    """Load a document based on its file extension."""
    path = Path(file_path)
    file_ext = path.suffix.lower()

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    documents = []
    page_count = 0

    if file_ext == ".pdf":
        loader = PDFReader()
        docs = loader.load_data(file=Path(file_path))
        for i, doc in enumerate(docs):
            doc.metadata["file_name"] = path.name
            doc.metadata["file_type"] = "pdf"
            doc.metadata["page_number"] = i + 1
            documents.append(doc)
        page_count = len(docs)

    elif file_ext in [".docx", ".doc"]:
        loader = DocxReader()
        docs = loader.load_data(file=Path(file_path))
        for doc in docs:
            doc.metadata["file_name"] = path.name
            doc.metadata["file_type"] = "docx"
            documents.append(doc)
        total_chars = sum(len(doc.text) for doc in docs)
        page_count = max(
            1, (total_chars // 3000) + (1 if total_chars % 3000 > 0 else 0)
        )

    elif file_ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        doc = Document(
            text=content,
            metadata={
                "file_name": path.name,
                "file_type": "txt",
            },
        )
        documents.append(doc)
        page_count = max(
            1, (len(content) // 3000) + (1 if len(content) % 3000 > 0 else 0)
        )

    else:
        raise ValueError(f"Unsupported file type: {file_ext}")

    for doc in documents:
        if "total_pages" not in doc.metadata:
            doc.metadata["total_pages"] = page_count

    return documents


def load_documents_from_directory(directory: str) -> List[Document]:
    """Load all supported documents from a directory."""
    reader = SimpleDirectoryReader(
        input_dir=directory,
        recursive=True,
    )
    documents = reader.load_data()

    for doc in documents:
        if "file_name" not in doc.metadata:
            doc.metadata["file_name"] = doc.metadata.get("file_path", "unknown")

    return documents
