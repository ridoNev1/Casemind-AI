from flask import jsonify, request

from . import blueprint
from ...auth import jwt_required
from ...services.audit_copilot import (
    ClaimNotFound,
    FeedbackValidationError,
    _ensure_claim_exists,
    generate_summary,
    record_feedback,
)
from ...services.chat_agent import generate_chat_reply
from ...services.chat_history import append_chat_message, list_chat_messages
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
        "discharge_start": request.args.get("discharge_start"),
        "discharge_end": request.args.get("discharge_end"),
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
        "discharge_start",
        "discharge_end",
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


@blueprint.route("/<claim_id>/summary")
@jwt_required
def claim_summary(claim_id: str):
    """Generate structured audit summary for a specific claim."""
    try:
        payload = generate_summary(claim_id)
    except ClaimNotFound as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"data": payload})


@blueprint.route("/<claim_id>/feedback", methods=["POST"])
@jwt_required
def claim_feedback(claim_id: str):
    """Persist auditor feedback for the given claim."""
    reviewer = getattr(request, "user", None)
    payload = request.get_json(silent=True) or {}
    try:
        outcome = record_feedback(claim_id, reviewer, payload)
    except ClaimNotFound as exc:
        return jsonify({"error": str(exc)}), 404
    except FeedbackValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"data": outcome.to_dict()}), 201


@blueprint.route("/<claim_id>/chat", methods=["GET"])
@jwt_required
def claim_chat_history(claim_id: str):
    """Return persisted chat messages for a claim."""
    try:
        _ensure_claim_exists(claim_id)
    except ClaimNotFound as exc:
        return jsonify({"error": str(exc)}), 404

    history = list_chat_messages(claim_id)
    return jsonify({"data": history})


@blueprint.route("/<claim_id>/chat", methods=["POST"])
@jwt_required
def claim_chat_interact(claim_id: str):
    """Record auditor question and return copilot reply."""
    try:
        _ensure_claim_exists(claim_id)
    except ClaimNotFound as exc:
        return jsonify({"error": str(exc)}), 404

    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message tidak boleh kosong"}), 400

    user = getattr(request, "user", None)
    sender = getattr(user, "email", None) or "auditor"
    user_msg = append_chat_message(
        claim_id=claim_id,
        sender=sender,
        role="user",
        content=message,
        metadata={"origin": "auditor"},
    )

    reply_text, llm_meta = generate_chat_reply(claim_id, message)
    bot_msg = append_chat_message(
        claim_id=claim_id,
        sender="copilot",
        role="assistant",
        content=reply_text,
        metadata=llm_meta,
    )

    return jsonify({"data": {"user_message": user_msg, "bot_message": bot_msg}})
