from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.auth.service import (
    login_user,
    logout_current_token,
    register_user,
    reset_password,
    start_password_reset,
)
from app.auth.utils import make_tokens
from app.extensions.db import db
from app.models.user import User
from app.utils.response import error_response, success_response

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    print(request.get_json())
    """
    ---
    tags: [Authentication]
    summary: Register a user
    description: Creates an account with role admin, agent, or customer.
    responses:
      201: {description: User registered}
    """
    user, errors = register_user(request.get_json() or {})
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("User registered successfully.", user.to_dict(), 201)


@auth_bp.post("/login")
def login():
    """
    ---
    tags: [Authentication]
    summary: Login
    description: Returns JWT access and refresh tokens.
    responses:
      200: {description: Login successful}
    """
    result = login_user(request.get_json() or {})
    if not result:
        return error_response("Invalid email or password.", 401)
    return success_response("Login successful.", result)


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """
    ---
    tags: [Authentication]
    summary: Refresh token
    description: Issues a new token pair from a refresh token.
    security: [{Bearer: []}]
    responses:
      200: {description: Tokens refreshed}
    """
    user = db.session.get(User, int(get_jwt_identity()))
    return success_response("Token refreshed.", make_tokens(user))


@auth_bp.post("/logout")
@jwt_required()
def logout():
    """
    ---
    tags: [Authentication]
    summary: Logout
    description: Revokes the current JWT.
    security: [{Bearer: []}]
    responses:
      200: {description: Logged out}
    """
    logout_current_token()
    return success_response("Logged out successfully.")


@auth_bp.post("/forgot-password")
def forgot_password():
    """
    ---
    tags: [Authentication]
    summary: Forgot password
    description: Sends a password reset token by email when the account exists.
    responses:
      200: {description: Reset email processed}
    """
    start_password_reset((request.get_json() or {}).get("email"))
    return success_response("If the account exists, a reset email has been sent.")


@auth_bp.post("/reset-password")
def reset():
    """
    ---
    tags: [Authentication]
    summary: Reset password
    description: Resets a user password with a valid reset token.
    responses:
      200: {description: Password reset}
    """
    errors = reset_password(request.get_json() or {})
    if errors:
        return error_response("Validation error", 400, errors)
    return success_response("Password reset successfully.")
