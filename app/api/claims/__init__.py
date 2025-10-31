from flask import Blueprint

blueprint = Blueprint("claims", __name__)

from . import routes  # noqa: E402
