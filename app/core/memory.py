from datetime import datetime
from typing import Dict, List, Optional

from app.config import settings


class ConversationMemory:
    """In-memory conversation history manager."""

    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = {}

    def add_message(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None
    ) -> None:
        """Add a message to the conversation history."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        if metadata:
            message["metadata"] = metadata

        self.sessions[session_id].append(message)

        if len(self.sessions[session_id]) > settings.max_conversation_history * 2:
            self.sessions[session_id] = self.sessions[session_id][
                -settings.max_conversation_history * 2 :
            ]

    def get_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session."""
        return self.sessions.get(session_id, [])

    def get_recent_history(self, session_id: str, n: int = None) -> List[Dict]:
        """Get recent conversation history."""
        if n is None:
            n = settings.max_conversation_history

        history = self.get_history(session_id)
        return history[-n:] if len(history) > n else history

    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def format_history_for_llm(self, session_id: str) -> str:
        """Format conversation history for LLM context."""
        history = self.get_recent_history(session_id)

        formatted = []
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            formatted.append(f"{role.capitalize()}: {content}")

        return "\n".join(formatted)


memory = ConversationMemory()
