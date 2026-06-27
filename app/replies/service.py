from app.extensions.db import db
from app.models.audit_log import AuditLog
from app.models.ticket_reply import TicketReply


def add_reply(ticket, user, data):
    message = (data.get("message") or "").strip()
    if len(message) < 1:
        return None, {"message": "Message is required."}
    reply = TicketReply(ticket_id=ticket.id, user_id=user.id, message=message)
    db.session.add(reply)
    db.session.add(AuditLog(user_id=user.id, action="ticket reply added", entity_type="ticket", entity_id=ticket.id))
    db.session.commit()
    return reply, None


def conversation(ticket):
    replies = TicketReply.query.filter_by(ticket_id=ticket.id).order_by(TicketReply.created_at.asc()).all()
    return [reply.to_dict() for reply in replies]
