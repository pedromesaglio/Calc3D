import hashlib
import secrets

from fastapi import Request

from .db import get_db
from .config import Config


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        Config.PBKDF2_ITERATIONS
    ).hex()
    return f"{salt}${h}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$")
        check = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            Config.PBKDF2_ITERATIONS
        ).hex()
        return secrets.compare_digest(check, h)
    except Exception:
        return False


def get_current_user(request: Request, db_path: str | None = None) -> dict | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT id, username, created_at FROM users WHERE id = ?", (uid,)
        ).fetchone()
        return dict(row) if row else None
