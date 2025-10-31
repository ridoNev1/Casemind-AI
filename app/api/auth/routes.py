from datetime import datetime, timedelta, timezone

from flask import current_app, jsonify, request

from ...services.auth import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    authenticate_user,
    generate_access_token,
    register_user,
)

from . import blueprint


@blueprint.route("/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    full_name = payload.get("full_name")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        user = register_user(email=email, password=password, full_name=full_name)
    except EmailAlreadyRegistered as exc:
        return jsonify({"error": str(exc)}), 409

    return (
        jsonify(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        ),
        201,
    )


@blueprint.route("/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        user = authenticate_user(email=email, password=password)
    except InvalidCredentials as exc:
        return jsonify({"error": str(exc)}), 401

    expires_in = current_app.config["JWT_ACCESS_EXPIRES_SECONDS"]
    token = generate_access_token(
        user=user,
        secret_key=current_app.config["SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
        expires_in_seconds=expires_in,
    )

    expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)

    return jsonify(
        {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "expires_at": expires_at.isoformat(),
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
            },
        }
    )
