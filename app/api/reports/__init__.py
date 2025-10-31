from flask import Blueprint

blueprint = Blueprint("reports", __name__)

from . import routes  # noqa: E402
