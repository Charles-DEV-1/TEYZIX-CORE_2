import pytest

from app import create_app
from app.auth.utils import hash_password
from app.extensions.db import db
from app.models.user import User


class TestConfig:
    TESTING = True
    SECRET_KEY = "test"
    JWT_SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = None
    RATE_LIMIT_ENABLED = False
    MAIL_SUPPRESS_SEND = True


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                User(name="Admin", email="admin@example.com", password_hash=hash_password("Admin@123"), role="admin"),
                User(name="Agent", email="agent@example.com", password_hash=hash_password("Agent@123"), role="agent"),
                User(
                    name="Customer",
                    email="customer@example.com",
                    password_hash=hash_password("Customer@123"),
                    role="customer",
                ),
            ]
        )
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password):
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.get_json()["data"]["access_token"]
