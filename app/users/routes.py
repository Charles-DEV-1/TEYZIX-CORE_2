from flask import Blueprint, request

from app.auth.decorators import roles_required
from app.extensions.db import db
from app.models.user import User
from app.users.service import create_agent, delete_user, update_user
from app.utils.response import error_response, success_response

users_bp = Blueprint("users", __name__)


@users_bp.post("/agents")
@roles_required("admin")
def add_agent():
    """
    ---
    tags: [Users]
    summary: Create agent
    description: Admin-only endpoint for creating support agents.
    security: [{Bearer: []}]
    responses:
      201: {description: Agent created}
    """
    user, errors = create_agent(request.get_json() or {})
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("Agent created successfully.", user.to_dict(), 201)


@users_bp.get("")
@roles_required("admin")
def list_users():
    """
    ---
    tags: [Users]
    summary: List users
    description: Admin-only list of all users.
    security: [{Bearer: []}]
    responses:
      200: {description: Users returned}
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return success_response("Users fetched successfully.", [user.to_dict() for user in users])


@users_bp.get("/<int:user_id>")
@roles_required("admin")
def get_user(user_id):
    """
    ---
    tags: [Users]
    summary: Get user
    description: Admin-only user detail endpoint.
    security: [{Bearer: []}]
    responses:
      200: {description: User returned}
    """
    user = db.get_or_404(User, user_id)
    return success_response("User fetched successfully.", user.to_dict())


@users_bp.put("/<int:user_id>")
@roles_required("admin")
def edit_user(user_id):
    """
    ---
    tags: [Users]
    summary: Update user
    description: Admin-only user update endpoint.
    security: [{Bearer: []}]
    responses:
      200: {description: User updated}
    """
    user = db.get_or_404(User, user_id)
    errors = update_user(user, request.get_json() or {})
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("User updated successfully.", user.to_dict())


@users_bp.delete("/<int:user_id>")
@roles_required("admin")
def remove_user(user_id):
    """
    ---
    tags: [Users]
    summary: Delete user
    description: Admin-only soft delete that deactivates the account.
    security: [{Bearer: []}]
    responses:
      200: {description: User deleted}
    """
    user = db.get_or_404(User, user_id)
    delete_user(user)
    return success_response("User deleted successfully.")
