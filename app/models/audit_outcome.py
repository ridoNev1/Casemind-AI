import uuid
from datetime import datetime

from ..extensions import db


class AuditOutcome(db.Model):
    __tablename__ = "audit_outcomes"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id = db.Column(db.String(64), nullable=False, index=True)
    decision = db.Column(db.String(32), nullable=False)
    correction_ratio = db.Column(db.Float)
    notes = db.Column(db.Text)
    reviewer_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    reviewer = db.relationship("User", backref="audit_outcomes")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "decision": self.decision,
            "correction_ratio": self.correction_ratio,
            "notes": self.notes,
            "reviewer_id": self.reviewer_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
