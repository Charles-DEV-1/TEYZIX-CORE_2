from app.models.ticket import Ticket
from app.models.user import User


def stats():
    return {
        "total_tickets": Ticket.query.count(),
        "open_tickets": Ticket.query.filter_by(status="open").count(),
        "resolved_tickets": Ticket.query.filter_by(status="resolved").count(),
        "closed_tickets": Ticket.query.filter_by(status="closed").count(),
        "active_agents": User.query.filter_by(role="agent", is_active=True).count(),
    }
