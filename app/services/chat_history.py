from __future__ import annotations

from typing import Any, Iterable

from ..extensions import db
from ..models import ChatMessage


def list_chat_messages(claim_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Return serialized chat history ordered by creation time asc."""
    query = ChatMessage.query.filter_by(claim_id=claim_id).order_by(ChatMessage.created_at.asc())
    if limit:
        query = query.limit(limit)
    return [msg.to_dict() for msg in query.all()]


def append_chat_message(
    claim_id: str,
    sender: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a chat bubble and return its serialized payload."""
    message = ChatMessage(
        claim_id=claim_id,
        sender=sender,
        role=role,
        content=content,
        extra=metadata or {},
    )
    db.session.add(message)
    db.session.commit()
    return message.to_dict()
