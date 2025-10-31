import os


def resolve_database_uri() -> str:
    """Ensure SQLAlchemy gets a usable connection string without hard-coded credentials."""
    default_uri = "sqlite:///instance/app.db"
    raw_uri = os.getenv("DATABASE_URL", default_uri)
    if raw_uri.startswith("postgresql://"):
        return raw_uri.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_uri


class BaseConfig:
    SQLALCHEMY_DATABASE_URI = resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    RULESET_VERSION = os.getenv("RULESET_VERSION", "RULESET_v1")
    DUCKDB_PATH = os.getenv("DUCKDB_PATH", os.path.join("instance", "analytics.duckdb"))
    API_TITLE = os.getenv("API_TITLE", "Casemind Claims API")
    API_VERSION = os.getenv("API_VERSION", "1.0.0")
    SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-key")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_EXPIRES_SECONDS = int(os.getenv("JWT_ACCESS_EXPIRES_SECONDS", "3600"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


config_by_name = {
    "default": BaseConfig,
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
