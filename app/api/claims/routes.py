from flask import jsonify, request

from . import blueprint
from ...auth import jwt_required
from ...services.risk_scoring import get_high_risk_claims


@blueprint.route("/high-risk")
@jwt_required
def high_risk_claims():
    """List high risk claims (placeholder payload until ETL ready)."""
    filters = {
        "province": request.args.get("province"),
        "dx": request.args.get("dx"),
    }
    claims = get_high_risk_claims(filters)
    return jsonify({"data": claims, "filters": filters})
