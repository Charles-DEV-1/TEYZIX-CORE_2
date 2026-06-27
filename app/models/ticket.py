from datetime import datetime, timezone
from uuid import uuid4

from app.extensions.db import db


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(40), nullable=False, unique=True, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="open", index=True)
    priority = db.Column(db.String(20), nullable=False, default="medium", index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assigned_agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    customer = db.relationship("User", foreign_keys=[customer_id], back_populates="customer_tickets")
    assigned_agent = db.relationship("User", foreign_keys=[assigned_agent_id], back_populates="assigned_tickets")
    replies = db.relationship("TicketReply", back_populates="ticket", cascade="all, delete-orphan", lazy=True)

    @staticmethod
    def new_ticket_number() -> str:
        return f"TCK-{uuid4().hex[:10].upper()}"

    def to_dict(self, include_users: bool = True):
        data = {
            "id": self.id,
            "ticket_number": self.ticket_number,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "customer_id": self.customer_id,
            "assigned_agent_id": self.assigned_agent_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_users:
            data["customer"] = self.customer.to_dict() if self.customer else None
            data["assigned_agent"] = self.assigned_agent.to_dict() if self.assigned_agent else None
        return data
