import os

from flask import Flask
from flask_migrate import Migrate

from app.extensions.bcrypt import bcrypt
from app.extensions.db import db
from app.extensions.jwt import jwt
from app.extensions.mail import mail
from app.extensions.rate_limiter import init_rate_limiter
from app.extensions.redis import init_redis, is_token_blacklisted
from app.swagger_config import init_swagger
from app.utils.response import error_response

migrate = Migrate()


def create_app(config_object=None):
    app = Flask(__name__)
    config_path = config_object or os.getenv("APP_CONFIG", "app.config.development.DevelopmentConfig")
    app.config.from_object(config_path)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    init_redis(app)
    init_rate_limiter(app)
    init_swagger(app)

    from app import models  # noqa: F401
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.replies.routes import replies_bp
    from app.tickets.routes import tickets_bp
    from app.users.routes import users_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(tickets_bp, url_prefix="/tickets")
    app.register_blueprint(replies_bp)
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

    register_error_handlers(app)
    register_jwt_handlers()

    @app.get("/")
    def health_check():
        return {"success": True, "message": "Customer Support Ticket API is running"}

    return app


def register_jwt_handlers():
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):  # noqa: ARG001
        return is_token_blacklisted(jwt_payload["jti"])

    @jwt.unauthorized_loader
    def missing_token(reason):
        return error_response(reason, 401)

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error_response(reason, 401)

    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_payload):  # noqa: ARG001
        return error_response("Token has been revoked.", 401)

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):  # noqa: ARG001
        return error_response("Token has expired.", 401)


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):  # noqa: ARG001
        return error_response("Bad request.", 400)

    @app.errorhandler(401)
    def unauthorized(error):  # noqa: ARG001
        return error_response("Unauthorized.", 401)

    @app.errorhandler(403)
    def forbidden(error):  # noqa: ARG001
        return error_response("Forbidden.", 403)

    @app.errorhandler(404)
    def not_found(error):  # noqa: ARG001
        return error_response("Resource not found.", 404)

    @app.errorhandler(500)
    def server_error(error):  # noqa: ARG001
        return error_response("Internal server error.", 500)
