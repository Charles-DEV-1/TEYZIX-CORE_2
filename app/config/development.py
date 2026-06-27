from app.config.base import BaseConfig


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///support_api_dev.db"
    REDIS_URL = None
