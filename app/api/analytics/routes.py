from flask import jsonify, request

from . import blueprint
from ...auth import jwt_required
from ...services.analytics import get_casemix_by_province
from ...services.qc_monitoring import get_qc_status


@blueprint.route("/casemix")
@jwt_required
def casemix():
    """Aggregate casemix metrics grouped by province."""
    limit = request.args.get("limit")
    parsed_limit = int(limit) if limit and limit.isdigit() else None
    data = get_casemix_by_province(limit=parsed_limit)
    return jsonify({"data": data})


@blueprint.route("/qc-status")
@jwt_required
def qc_status():
    """Return QC status for ML scoring pipeline."""
    status_payload = get_qc_status()
    return jsonify(status_payload)
