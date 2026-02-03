import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.logging import logger, setup_logging
from app.core.rate_limit import limiter
from app.core.routers import router
from app.auth.auth_router import auth_router
from app.core.database import init_db

# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("DocuQuery API starting up...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("DocuQuery API shutting down...")


app = FastAPI(
    title="DocuQuery API",
    description="""
## Intelligent Document Knowledge Base

DocuQuery is a RAG (Retrieval-Augmented Generation) system that allows users to upload documents
and ask natural language questions, receiving accurate answers with source citations.

### Features
- **Multi-format support**: PDF, DOCX, and TXT files
- **Hybrid Search**: Combines semantic vectors with BM25 keyword matching
- **Cohere Reranking**: Improves retrieval relevance by 5-15%
- **Source Citations**: Every answer includes exact document chunks with page numbers
- **Conversation Memory**: Follow-up questions maintain context
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)


@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    logger.info("Health check called")
    return {"ok": True, "service": "DocuQuery API", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
