from flask import Blueprint, request

from app.auth.decorators import current_user, roles_required
from app.extensions.db import db
from app.models.ticket import Ticket
from app.tickets.service import (
    assign_ticket,
    change_ticket_status,
    close_ticket,
    create_ticket,
    filter_tickets,
    get_visible_ticket,
    reopen_ticket,
    update_ticket,
)
from app.utils.response import error_response, success_response

tickets_bp = Blueprint("tickets", __name__)


@tickets_bp.post("")
@roles_required("customer")
def add_ticket():
    """
    ---
    tags: [Tickets]
    summary: Create ticket
    description: Customer-only ticket creation endpoint.
    security: [{Bearer: []}]
    responses:
      201: {description: Ticket created}
    """
    ticket, errors = create_ticket(request.get_json() or {}, current_user())
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("Ticket created successfully.", ticket.to_dict(), 201)


@tickets_bp.get("/my-tickets")
@roles_required("customer")
def my_tickets():
    """
    ---
    tags: [Tickets]
    summary: Get my tickets
    description: Returns tickets owned by the current customer.
    security: [{Bearer: []}]
    responses:
      200: {description: Tickets returned}
    """
    user = current_user()
    tickets = Ticket.query.filter_by(customer_id=user.id).order_by(Ticket.created_at.desc()).all()
    return success_response("Tickets fetched successfully.", [ticket.to_dict() for ticket in tickets])


@tickets_bp.get("/<int:ticket_id>")
@roles_required("admin", "agent", "customer")
def get_ticket(ticket_id):
    """
    ---
    tags: [Tickets]
    summary: Get ticket
    description: Returns a ticket when the user is allowed to view it.
    security: [{Bearer: []}]
    responses:
      200: {description: Ticket returned}
    """
    ticket = get_visible_ticket(ticket_id, current_user())
    if not ticket:
        return error_response("Ticket not found or access denied.", 403)
    return success_response("Ticket fetched successfully.", ticket.to_dict())


@tickets_bp.patch("/<int:ticket_id>")
@roles_required("admin", "customer")
def update(ticket_id):
    """
    ---
    tags: [Tickets]
    summary: Update ticket information
    description: Allows an admin or the owning customer to update ticket title, description, or priority.
    security: [{Bearer: []}]
    responses:
      200: {description: Ticket updated}
    """
    user = current_user()
    ticket = get_visible_ticket(ticket_id, user)
    if not ticket:
        return error_response("Ticket not found or access denied.", 403)
    errors = update_ticket(ticket, request.get_json() or {}, user)
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("Ticket updated successfully.", ticket.to_dict())


@tickets_bp.get("")
@roles_required("admin")
def all_tickets():
    """
    ---
    tags: [Tickets]
    summary: Get all tickets
    description: Admin-only ticket list with search and filters.
    security: [{Bearer: []}]
    responses:
      200: {description: Tickets returned}
    """
    try:
        tickets = filter_tickets(request.args)
    except ValueError:
        return error_response("Validation error", 400, {"date": "Use YYYY-MM-DD date format."})
    return success_response("Tickets fetched successfully.", [ticket.to_dict() for ticket in tickets])


@tickets_bp.patch("/<int:ticket_id>/assign")
@roles_required("admin")
def assign(ticket_id):
    """
    ---
    tags: [Tickets]
    summary: Assign ticket
    description: Admin-only endpoint for assigning tickets to agents.
    security: [{Bearer: []}]
    responses:
      200: {description: Ticket assigned}
    """
    ticket = db.get_or_404(Ticket, ticket_id)
    errors = assign_ticket(ticket, (request.get_json() or {}).get("agent_id"), current_user())
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("Ticket assigned successfully.", ticket.to_dict())


@tickets_bp.patch("/<int:ticket_id>/status")
@roles_required("admin", "agent")
def status(ticket_id):
    """
    ---
    tags: [Tickets]
    summary: Change status
    description: Agent or admin endpoint that follows the status workflow.
    security: [{Bearer: []}]
    responses:
      200: {description: Status changed}
    """
    user = current_user()
    ticket = get_visible_ticket(ticket_id, user)
    if not ticket:
        return error_response("Ticket not found or access denied.", 403)
    errors = change_ticket_status(ticket, (request.get_json() or {}).get("status"), user)
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("Ticket status updated successfully.", ticket.to_dict())


@tickets_bp.patch("/<int:ticket_id>/close")
@roles_required("admin")
def close(ticket_id):
    """
    ---
    tags: [Tickets]
    summary: Close ticket
    description: Admin-only endpoint for closing resolved tickets.
    security: [{Bearer: []}]
    responses:
      200: {description: Ticket closed}
    """
    ticket = db.get_or_404(Ticket, ticket_id)
    errors = close_ticket(ticket, current_user())
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("Ticket closed successfully.", ticket.to_dict())


@tickets_bp.patch("/<int:ticket_id>/reopen")
@roles_required("admin")
def reopen(ticket_id):
    """
    ---
    tags: [Tickets]
    summary: Reopen ticket
    description: Admin-only endpoint for reopening closed tickets.
    security: [{Bearer: []}]
    responses:
      200: {description: Ticket reopened}
    """
    ticket = db.get_or_404(Ticket, ticket_id)
    errors = reopen_ticket(ticket, current_user())
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("Ticket reopened successfully.", ticket.to_dict())
