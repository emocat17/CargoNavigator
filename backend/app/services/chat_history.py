"""Chat history persistence service."""
import json
import logging
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models.chat_models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


def create_session(title: str = "新对话") -> str:
    """Create a new chat session and return its ID."""
    db = SessionLocal()
    try:
        session = ChatSession(title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()


def save_message(
    session_id: str,
    role: str,
    content: str,
    route_context: Optional[str] = None,
    assessment_data: Optional[str] = None,
) -> str:
    """Save a message to a session and return the message ID."""
    db = SessionLocal()
    try:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            route_context=route_context,
            assessment_data=assessment_data,
        )
        db.add(msg)
        # Update session updated_at
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.updated_at = datetime.utcnow()
            # Auto-title from first user message
            if session.title == "新对话" and role == "user":
                session.title = content[:50] + ("..." if len(content) > 50 else "")
        db.commit()
        db.refresh(msg)
        return msg.id
    finally:
        db.close()


def get_session(session_id: str) -> Optional[dict]:
    """Get a session with all its messages."""
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return None
        return {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "route_context": json.loads(m.route_context) if m.route_context else None,
                    "assessment_data": json.loads(m.assessment_data) if m.assessment_data else None,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in session.messages
            ],
        }
    finally:
        db.close()


def list_sessions(limit: int = 50) -> list[dict]:
    """List recent chat sessions."""
    db = SessionLocal()
    try:
        sessions = (
            db.query(ChatSession)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "message_count": len(s.messages),
            }
            for s in sessions
        ]
    finally:
        db.close()


def delete_session(session_id: str) -> bool:
    """Delete a session and all its messages."""
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return False
        db.delete(session)
        db.commit()
        return True
    finally:
        db.close()
