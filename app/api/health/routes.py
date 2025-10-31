from flask import jsonify

from . import blueprint


@blueprint.route("/ping")
def ping():
    """Basic liveness probe."""
    return jsonify({"status": "ok"})
