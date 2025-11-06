from flask import jsonify, request

from . import blueprint
from ...auth import jwt_required
from ...services.reports import (
    get_duplicate_claims,
    get_severity_mismatch,
    get_tariff_insight,
)


def _parse_limit() -> int | None:
    raw = request.args.get("limit")
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


@blueprint.route("/severity-mismatch")
@jwt_required
def severity_mismatch():
    """Return severity mismatch claims derived from claims_normalized."""
    limit = _parse_limit()
    data = get_severity_mismatch(limit=limit or 200)
    return jsonify({"data": data})


@blueprint.route("/duplicates")
@jwt_required
def duplicate_claims():
    """Return duplicate claim candidates within a three-day window."""
    limit = _parse_limit()
    data = get_duplicate_claims(limit=limit or 200)
    return jsonify({"data": data})


@blueprint.route("/tariff-insight")
@jwt_required
def tariff_insight():
    """Return tariff gap insight per facility and casemix group."""
    limit = _parse_limit() or 100
    province = request.args.get("province")
    facility_id = request.args.get("facility_id")
    severity = request.args.get("severity")
    service_type = request.args.get("service_type")
    dx_group = request.args.get("dx_group")

    data = get_tariff_insight(
        limit=limit,
        province=province,
        facility_id=facility_id,
        severity=severity,
        service_type=service_type,
        dx_group=dx_group,
    )
    return jsonify({"data": data})
