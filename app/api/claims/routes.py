from flask import jsonify, request

from . import blueprint
from ...auth import jwt_required
from ...services.risk_scoring import get_high_risk_claims


@blueprint.route("/high-risk")
@jwt_required
def high_risk_claims():
    """List high risk claims scored by rules + ML."""
    filters = {
        "province": request.args.get("province"),
        "dx": request.args.get("dx"),
        "page": request.args.get("page"),
        "page_size": request.args.get("page_size"),
        "limit": request.args.get("limit"),
        "refresh_cache": request.args.get("refresh_cache"),
        "severity": request.args.get("severity"),
        "service_type": request.args.get("service_type"),
        "min_risk_score": request.args.get("min_risk_score"),
        "max_risk_score": request.args.get("max_risk_score"),
        "min_ml_score": request.args.get("min_ml_score"),
        "facility_class": request.args.get("facility_class"),
        "start_date": request.args.get("start_date"),
        "end_date": request.args.get("end_date"),
    }
    result = get_high_risk_claims(filters)

    filter_keys = {
        "province",
        "dx",
        "severity",
        "service_type",
        "min_risk_score",
        "max_risk_score",
        "min_ml_score",
        "facility_class",
        "start_date",
        "end_date",
    }
    applied_filters = {key: value for key, value in filters.items() if key in filter_keys and value}

    return jsonify(
        {
            "data": result["items"],
            "meta": {
                "total": result["total"],
                "page": result["page"],
                "page_size": result["page_size"],
                "model_version": result["model_version"],
                "ruleset_version": result["ruleset_version"],
                "filters": applied_filters,
            },
        }
    )
