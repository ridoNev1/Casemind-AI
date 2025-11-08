import os

from dotenv import load_dotenv

load_dotenv()


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
    OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY") or os.getenv("OPENAI_API_KEY")
    COPILOT_LLM_PROVIDER = os.getenv("COPILOT_LLM_PROVIDER", "openai")
    COPILOT_LLM_MODEL = os.getenv("COPILOT_LLM_MODEL", "gpt-4o-mini")
    COPILOT_LLM_TEMPERATURE = float(os.getenv("COPILOT_LLM_TEMPERATURE", "0.2"))
    COPILOT_LLM_MAX_TOKENS = int(os.getenv("COPILOT_LLM_MAX_TOKENS", "400"))
    COPILOT_CACHE_DIR = os.getenv("COPILOT_CACHE_DIR", os.path.join("instance", "cache", "copilot"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


config_by_name = {
    "default": BaseConfig,
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
