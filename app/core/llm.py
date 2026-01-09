from typing import List, Optional

from llama_index.core.llms import LLM
from llama_index.core.schema import NodeWithScore
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.openai import OpenAI

from app.config import settings


def get_llm() -> LLM:
    """Get LLM instance based on configuration."""
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment variables")
        return Anthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
        )
    else:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set in environment variables")
        model = (
            settings.llm_model
            if settings.llm_model.startswith("gpt")
            else "gpt-4o-mini"
        )
        return OpenAI(
            model=model,
            api_key=settings.openai_api_key,
        )


def generate_answer(
    query: str,
    retrieved_nodes: List[NodeWithScore],
    conversation_history: Optional[str] = None,
) -> str:
    """Generate answer from retrieved context."""
    llm = get_llm()

    context_parts = []
    for i, node in enumerate(retrieved_nodes, 1):
        content = node.node.get_content()
        metadata = node.node.metadata
        file_name = metadata.get("file_name", "unknown")
        page = metadata.get("page_number", "")
        page_info = f" (page {page})" if page else ""

        context_parts.append(f"[Source {i} - {file_name}{page_info}]\n{content}\n")

    context = "\n".join(context_parts)

    history_text = ""
    if conversation_history:
        history_text = f"\n\nPrevious conversation:\n{conversation_history}\n"

    prompt = f"""You are a helpful assistant that answers questions based on the provided document context. 
Use only the information from the sources below to answer the question. If the answer cannot be found in the sources, say so.

Sources:
{context}

{history_text}
Question: {query}

Answer:"""

    response = llm.complete(prompt)
    return str(response).strip()
