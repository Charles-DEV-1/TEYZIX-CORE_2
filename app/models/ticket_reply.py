from datetime import datetime, timezone

from app.extensions.db import db


class TicketReply(db.Model):
    __tablename__ = "ticket_replies"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    ticket = db.relationship("Ticket", back_populates="replies")
    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "user_id": self.user_id,
            "user": self.user.to_dict() if self.user else None,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
