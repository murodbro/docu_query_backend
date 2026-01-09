import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    cohere_api_key: str = os.getenv("COHERE_API_KEY", "")

    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")

    llm_model: str = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")  # "anthropic" or "openai"

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    top_k: int = int(os.getenv("TOP_K", "20"))
    rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "5"))
    hybrid_search_weight: float = float(os.getenv("HYBRID_SEARCH_WEIGHT", "0.5"))

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "80"))

    max_conversation_history: int = int(os.getenv("MAX_CONVERSATION_HISTORY", "10"))


settings = Settings()
