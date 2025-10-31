from flask import Flask

from .analytics import blueprint as analytics_blueprint
from .auth import blueprint as auth_blueprint
from .claims import blueprint as claims_blueprint
from .docs import blueprint as docs_blueprint
from .health import blueprint as health_blueprint
from .reports import blueprint as reports_blueprint


def register_blueprints(app: Flask) -> None:
    """Wire all HTTP blueprints into the Flask app."""
    app.register_blueprint(health_blueprint, url_prefix="/health")
    app.register_blueprint(auth_blueprint, url_prefix="/auth")
    app.register_blueprint(claims_blueprint, url_prefix="/claims")
    app.register_blueprint(reports_blueprint, url_prefix="/reports")
    app.register_blueprint(analytics_blueprint, url_prefix="/analytics")
    app.register_blueprint(docs_blueprint, url_prefix="/docs")
