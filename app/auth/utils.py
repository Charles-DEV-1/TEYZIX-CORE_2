from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from flask_jwt_extended import create_access_token, create_refresh_token

from app.extensions.bcrypt import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.generate_password_hash(password).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.check_password_hash(password_hash, password)


def make_tokens(user):
    extra_claims = {"email": user.email, "role": user.role}
    identity = str(user.id)
    return {
        "access_token": create_access_token(identity=identity, additional_claims=extra_claims),
        "refresh_token": create_refresh_token(identity=identity, additional_claims=extra_claims),
    }


def make_reset_token(user):
    plain_token = token_urlsafe(32)
    user.reset_token_hash = hash_password(plain_token)
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return plain_token
