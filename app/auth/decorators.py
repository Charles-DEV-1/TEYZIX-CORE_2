from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from app.extensions.db import db
from app.models.user import User
from app.utils.response import error_response


def roles_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") not in roles:
                return error_response("You do not have permission to perform this action.", 403)
            return fn(*args, **kwargs)

        return decorated

    return wrapper


def current_user():
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id)) if user_id else None
