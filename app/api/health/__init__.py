from flask import Blueprint

blueprint = Blueprint("health", __name__)

from . import routes  # noqa: E402
