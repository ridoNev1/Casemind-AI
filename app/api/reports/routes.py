from flask import jsonify

from . import blueprint
from ...auth import jwt_required
from ...services.reports import get_duplicate_claims, get_severity_mismatch


@blueprint.route("/severity-mismatch")
@jwt_required
def severity_mismatch():
    """Placeholder severity mismatch feed."""
    data = get_severity_mismatch()
    return jsonify({"data": data})


@blueprint.route("/duplicates")
@jwt_required
def duplicate_claims():
    """Placeholder duplicate claims feed."""
    data = get_duplicate_claims()
    return jsonify({"data": data})
