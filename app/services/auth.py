from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User


class AuthServiceError(Exception):
    """Base class for auth related errors."""


class InvalidCredentials(AuthServiceError):
    """Raised when login credentials are invalid."""


class EmailAlreadyRegistered(AuthServiceError):
    """Raised when attempting to register an email that already exists."""


class TokenExpired(AuthServiceError):
    """Raised when a JWT is expired."""


class TokenInvalid(AuthServiceError):
    """Raised when a JWT cannot be decoded."""


def register_user(email: str, password: str, full_name: Optional[str] = None, role: str = "auditor") -> User:
    """Create a new user with hashed password."""
    normalized_email = email.strip().lower()

    if User.query.filter_by(email=normalized_email).first():
        raise EmailAlreadyRegistered("Email is already registered")

    user = User(
        email=normalized_email,
        password_hash=generate_password_hash(password),
        full_name=full_name,
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return user


def authenticate_user(email: str, password: str) -> User:
    """Validate credentials and return the user instance."""
    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user or not check_password_hash(user.password_hash, password):
        raise InvalidCredentials("Invalid email or password")
    return user


def generate_access_token(user: User, secret_key: str, algorithm: str, expires_in_seconds: int) -> str:
    """Generate a signed JWT for the given user."""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in_seconds),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_token(token: str, secret_key: str, algorithm: str) -> dict:
    """Validate a JWT and return the decoded payload."""
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpired("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalid("Token is invalid") from exc
