from flask import Blueprint

blueprint = Blueprint("analytics", __name__)

from . import routes  # noqa: E402
