from functools import wraps
from typing import Callable, Optional

from flask import current_app, jsonify, request

from ..models import User
from ..services.auth import TokenExpired, TokenInvalid, decode_token


def extract_token_from_header() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def get_current_user() -> Optional[User]:
    """Return user associated with Authorization header; returns None if invalid."""
    token = extract_token_from_header()
    if not token:
        return None

    try:
        payload = decode_token(
            token,
            current_app.config["SECRET_KEY"],
            current_app.config["JWT_ALGORITHM"],
        )
    except (TokenExpired, TokenInvalid):
        return None

    return User.query.filter_by(id=payload.get("sub")).first()


def jwt_required(fn: Callable):
    """Decorator enforcing valid JWT bearer token."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = extract_token_from_header()
        if not token:
            return jsonify({"error": "Authorization header missing or malformed"}), 401

        try:
            payload = decode_token(
                token,
                current_app.config["SECRET_KEY"],
                current_app.config["JWT_ALGORITHM"],
            )
        except TokenExpired:
            return jsonify({"error": "Token has expired"}), 401
        except TokenInvalid:
            return jsonify({"error": "Token is invalid"}), 401

        user = User.query.filter_by(id=payload.get("sub")).first()
        if not user:
            return jsonify({"error": "User not found"}), 401

        # Attach user to request context for downstream handlers to use.
        request.user = user  # type: ignore[attr-defined]
        return fn(*args, **kwargs)

    return wrapper
