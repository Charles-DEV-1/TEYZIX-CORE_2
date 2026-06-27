from datetime import datetime, timezone

from flask_jwt_extended import get_jwt

from app.auth.utils import hash_password, make_reset_token, make_tokens, verify_password
from app.extensions.db import db
from app.extensions.redis import blacklist_token
from app.models.user import User
from app.notifications.email_service import send_email
from app.utils.validators import validate_email, validate_password, validate_phone


def register_user(data):
    errors = {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").lower().strip()
    password = data.get("password")
    phone_number = data.get("phone_number")

    if not name:
        errors["name"] = "Name is required."
    if not validate_email(email):
        errors["email"] = "Valid email is required."
    password_ok, password_error = validate_password(password)
    if not password_ok:
        errors["password"] = password_error
    if not validate_phone(phone_number):
        errors["phone_number"] = "Phone number is invalid."
    if User.query.filter_by(email=email).first():
        errors["email"] = "Email already exists."
    if errors:
        return None, errors

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="customer",
        phone_number=phone_number,
    )
    db.session.add(user)
    db.session.commit()
    return user, None


def login_user(data):
    email = (data.get("email") or "").lower().strip()
    password = data.get("password")
    user = User.query.filter_by(email=email).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return {"user": user.to_dict(), **make_tokens(user)}


def logout_current_token():
    claims = get_jwt()
    expires_at = claims["exp"] - int(datetime.now(timezone.utc).timestamp())
    blacklist_token(claims["jti"], max(expires_at, 1))


def start_password_reset(email: str):
    user = User.query.filter_by(email=(email or "").lower().strip()).first()
    if not user:
        return
    token = make_reset_token(user)
    db.session.commit()
    send_email(
        to=user.email,
        subject="Password Reset",
        body=f"Use this token to reset your password: {token}",
    )


def reset_password(data):
    email = (data.get("email") or "").lower().strip()
    token = data.get("token")
    password = data.get("password")
    user = User.query.filter_by(email=email).first()
    password_ok, password_error = validate_password(password)
    if not user or not user.reset_token_hash:
        return {"token": "Reset token is invalid."}
    expires_at = user.reset_token_expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not expires_at or expires_at < datetime.now(timezone.utc):
        return {"token": "Reset token has expired."}
    if not verify_password(token, user.reset_token_hash):
        return {"token": "Reset token is invalid."}
    if not password_ok:
        return {"password": password_error}

    user.password_hash = hash_password(password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.session.commit()
    return None
