from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    folder_id: Optional[str] = None  # Filter by specific folder


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    session_id: str


task_statuses: Dict[str, Dict] = {}


class TaskStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
