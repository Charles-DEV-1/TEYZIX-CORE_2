from flask import Blueprint, request

from app.auth.decorators import current_user, roles_required
from app.replies.service import add_reply, conversation
from app.tickets.service import get_visible_ticket
from app.utils.response import error_response, success_response

replies_bp = Blueprint("replies", __name__)


@replies_bp.post("/tickets/<int:ticket_id>/replies")
@roles_required("admin", "agent", "customer")
def create_reply(ticket_id):
    """
    ---
    tags: [Replies]
    summary: Add reply
    description: Adds a reply when the current user can access the ticket.
    security: [{Bearer: []}]
    responses:
      201: {description: Reply added}
    """
    user = current_user()
    ticket = get_visible_ticket(ticket_id, user)
    if not ticket:
        return error_response("Ticket not found or access denied.", 403)
    reply, errors = add_reply(ticket, user, request.get_json() or {})
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("Reply added successfully.", reply.to_dict(), 201)


@replies_bp.get("/tickets/<int:ticket_id>/replies")
@roles_required("admin", "agent", "customer")
def get_replies(ticket_id):
    """
    ---
    tags: [Replies]
    summary: Get conversation history
    description: Returns replies ordered by creation date.
    security: [{Bearer: []}]
    responses:
      200: {description: Conversation returned}
    """
    user = current_user()
    ticket = get_visible_ticket(ticket_id, user)
    if not ticket:
        return error_response("Ticket not found or access denied.", 403)
    return success_response("Conversation fetched successfully.", conversation(ticket))
