from app.auth.utils import hash_password
from app.extensions.db import db
from app.models.user import User
from app.utils.validators import validate_email, validate_password, validate_phone, validate_role


def create_agent(data):
    data = dict(data or {})
    data["role"] = "agent"
    return create_user(data)


def create_user(data):
    errors = validate_user_payload(data, creating=True)
    email = (data.get("email") or "").lower().strip()
    if User.query.filter_by(email=email).first():
        errors["email"] = "Email already exists."
    if errors:
        return None, errors

    user = User(
        name=data["name"].strip(),
        email=email,
        password_hash=hash_password(data["password"]),
        role=data["role"],
        phone_number=data.get("phone_number"),
        is_active=data.get("is_active", True),
    )
    db.session.add(user)
    db.session.commit()
    return user, None


def update_user(user, data):
    errors = validate_user_payload(data, creating=False)
    email = (data.get("email") or "").lower().strip() if data.get("email") else None
    if email and User.query.filter(User.email == email, User.id != user.id).first():
        errors["email"] = "Email already exists."
    if errors:
        return errors

    for field in ("name", "phone_number", "role", "is_active"):
        if field in data:
            setattr(user, field, data[field])
    if email:
        user.email = email
    if data.get("password"):
        user.password_hash = hash_password(data["password"])
    db.session.commit()
    return None


def delete_user(user):
    user.is_active = False
    db.session.commit()


def validate_user_payload(data, creating: bool):
    errors = {}
    if creating and not (data.get("name") or "").strip():
        errors["name"] = "Name is required."
    if data.get("email") or creating:
        if not validate_email((data.get("email") or "").lower().strip()):
            errors["email"] = "Valid email is required."
    if data.get("password") or creating:
        ok, message = validate_password(data.get("password"))
        if not ok:
            errors["password"] = message
    if data.get("phone_number") and not validate_phone(data.get("phone_number")):
        errors["phone_number"] = "Phone number is invalid."
    if data.get("role") and not validate_role(data.get("role")):
        errors["role"] = "Role must be admin, agent, or customer."
    return errors
