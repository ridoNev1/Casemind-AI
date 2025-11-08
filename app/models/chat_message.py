import uuid
from datetime import datetime

from ..extensions import db


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = db.Column(db.String(64), nullable=False, index=True)
    sender = db.Column(db.String(64), nullable=False)  # e.g., auditor email / "copilot"
    role = db.Column(db.String(32), nullable=False, default="user")  # user|assistant|system
    content = db.Column(db.Text, nullable=False)
    extra = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "sender": self.sender,
            "role": self.role,
            "content": self.content,
            "metadata": self.extra or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
