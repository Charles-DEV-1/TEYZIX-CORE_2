from datetime import datetime

from app.extensions.db import db
from app.models.audit_log import AuditLog
from app.models.ticket import Ticket
from app.models.user import User
from app.notifications.email_service import send_email
from app.tickets.validators import validate_status_change, validate_ticket_payload
from app.utils.validators import required_text, validate_priority


def create_ticket(data, customer):
    errors = validate_ticket_payload(data)
    if errors:
        return None, errors
    ticket = Ticket(
        ticket_number=Ticket.new_ticket_number(),
        title=data["title"].strip(),
        description=data["description"].strip(),
        priority=data.get("priority", "medium"),
        customer_id=customer.id,
    )
    db.session.add(ticket)
    db.session.flush()
    add_audit(customer.id, "ticket created", "ticket", ticket.id)
    db.session.commit()
    send_email(customer.email, "Ticket Created", f"Your ticket {ticket.ticket_number} has been created.")
    return ticket, None


def update_ticket(ticket, data, user):
    errors = {}
    if user.role == "customer" and ticket.customer_id != user.id:
        return {"ticket": "You can only update your own tickets."}
    if ticket.status == "closed":
        return {"status": "Closed tickets cannot be updated."}

    if "title" in data and not required_text(data.get("title"), 3, 180):
        errors["title"] = "Title must be between 3 and 180 characters."
    if "description" in data and not required_text(data.get("description"), 10, 5000):
        errors["description"] = "Description must be between 10 and 5000 characters."
    if "priority" in data and not validate_priority(data.get("priority")):
        errors["priority"] = "Priority must be low, medium, high, or urgent."
    if errors:
        return errors

    for field in ("title", "description", "priority"):
        if field in data:
            value = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(ticket, field, value)
    add_audit(user.id, "ticket updated", "ticket", ticket.id)
    db.session.commit()
    return None


def get_visible_ticket(ticket_id, user):
    ticket = db.get_or_404(Ticket, ticket_id)
    if user.role == "admin":
        return ticket
    if user.role == "customer" and ticket.customer_id == user.id:
        return ticket
    if user.role == "agent" and ticket.assigned_agent_id == user.id:
        return ticket
    return None


def filter_tickets(args):
    query = Ticket.query
    if args.get("title"):
        query = query.filter(Ticket.title.ilike(f"%{args['title']}%"))
    if args.get("status"):
        query = query.filter(Ticket.status == args["status"])
    if args.get("priority"):
        query = query.filter(Ticket.priority == args["priority"])
    if args.get("agent"):
        query = query.filter(Ticket.assigned_agent_id == int(args["agent"]))
    if args.get("customer"):
        customer = f"%{args['customer']}%"
        query = query.join(User, Ticket.customer_id == User.id).filter(User.name.ilike(customer))
    if args.get("date"):
        date_value = datetime.strptime(args["date"], "%Y-%m-%d").date()
        query = query.filter(db.func.date(Ticket.created_at) == date_value)
    return query.order_by(Ticket.created_at.desc()).all()


def assign_ticket(ticket, agent_id, admin):
    agent = User.query.filter_by(id=agent_id, role="agent", is_active=True).first()
    if not agent:
        return {"agent_id": "Active agent was not found."}
    ticket.assigned_agent_id = agent.id
    if ticket.status == "open":
        ticket.status = "in_progress"
    add_audit(admin.id, "ticket assigned", "ticket", ticket.id)
    db.session.commit()
    send_email(agent.email, "Ticket Assigned", f"Ticket {ticket.ticket_number} has been assigned to you.")
    return None


def change_ticket_status(ticket, new_status, user):
    error = validate_status_change(ticket.status, new_status)
    if error:
        return {"status": error}
    ticket.status = new_status
    add_audit(user.id, f"ticket {new_status}", "ticket", ticket.id)
    db.session.commit()
    if new_status == "resolved":
        send_email(ticket.customer.email, "Ticket Resolved", f"Ticket {ticket.ticket_number} has been resolved.")
    return None


def close_ticket(ticket, user):
    if ticket.status != "resolved":
        return {"status": "Only resolved tickets can be closed."}
    ticket.status = "closed"
    add_audit(user.id, "ticket closed", "ticket", ticket.id)
    db.session.commit()
    return None


def reopen_ticket(ticket, user):
    if ticket.status == "closed":
        ticket.status = "open"
        add_audit(user.id, "ticket reopened", "ticket", ticket.id)
        db.session.commit()
        return None
    return {"status": "Only closed tickets can be reopened by an admin."}


def add_audit(user_id, action, entity_type, entity_id):
    db.session.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id))
