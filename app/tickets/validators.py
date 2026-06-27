from app.utils.constants import STATUS_TRANSITIONS
from app.utils.validators import required_text, validate_priority, validate_status


def validate_ticket_payload(data):
    errors = {}
    if not required_text(data.get("title"), 3, 180):
        errors["title"] = "Title must be between 3 and 180 characters."
    if not required_text(data.get("description"), 10, 5000):
        errors["description"] = "Description must be between 10 and 5000 characters."
    priority = data.get("priority", "medium")
    if not validate_priority(priority):
        errors["priority"] = "Priority must be low, medium, high, or urgent."
    return errors


def validate_status_change(current_status: str, new_status: str):
    if not validate_status(new_status):
        return "Status must be open, in_progress, resolved, or closed."
    if new_status not in STATUS_TRANSITIONS[current_status]:
        return f"Cannot move ticket from {current_status} to {new_status}."
    return None
