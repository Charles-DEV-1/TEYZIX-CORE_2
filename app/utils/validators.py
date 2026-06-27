import re

from app.utils.constants import PRIORITIES, ROLES, STATUSES


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9\-\s]{7,20}$")


def validate_email(email: str) -> bool:
    return bool(email and EMAIL_RE.match(email))


def validate_password(password: str) -> tuple[bool, str]:
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    checks = [
        (r"[A-Z]", "one uppercase letter"),
        (r"[a-z]", "one lowercase letter"),
        (r"\d", "one number"),
        (r"[^A-Za-z0-9]", "one special character"),
    ]
    for pattern, label in checks:
        if not re.search(pattern, password):
            return False, f"Password must contain {label}."
    return True, ""


def validate_phone(phone_number: str | None) -> bool:
    return phone_number in (None, "") or bool(PHONE_RE.match(phone_number))


def validate_role(role: str) -> bool:
    return role in ROLES


def validate_status(status: str) -> bool:
    return status in STATUSES


def validate_priority(priority: str) -> bool:
    return priority in PRIORITIES


def required_text(value: str | None, min_length: int, max_length: int) -> bool:
    return bool(value and min_length <= len(value.strip()) <= max_length)
