from flask import Blueprint

blueprint = Blueprint("docs", __name__)

from . import routes  # noqa: E402
