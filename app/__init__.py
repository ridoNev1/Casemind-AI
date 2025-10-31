from flask import Flask, jsonify

from .api import register_blueprints
from .config import config_by_name
from .extensions import db


def create_app(config_name: str | None = None) -> Flask:
    """Application factory configuring extensions and blueprints."""
    app = Flask(__name__, instance_relative_config=True)

    selected_name = config_name or app.config.get("ENV", "development")
    base_config = config_by_name["default"]
    app.config.from_object(base_config)

    if selected_name in config_by_name:
        app.config.from_object(config_by_name[selected_name])

    app.config.from_pyfile("config.py", silent=True)

    db.init_app(app)

    register_blueprints(app)

    setup_cors_headers(app)
    register_error_handlers(app)

    return app


def setup_cors_headers(app: Flask) -> None:
    """Allow cross-origin requests for all endpoints (development default)."""

    @app.after_request
    def apply_cors(response):
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
        response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.setdefault("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        return response


def register_error_handlers(app: Flask) -> None:
    """Provide JSON responses for common errors."""

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
