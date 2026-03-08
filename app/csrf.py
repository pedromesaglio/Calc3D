import secrets

from fastapi import Form, HTTPException, Request
from markupsafe import Markup

_SESSION_KEY = "_csrf"


def get_csrf_token(request: Request) -> str:
    token = request.session.get(_SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)
        request.session[_SESSION_KEY] = token
    return token


def validate_csrf(request: Request, token: str) -> None:
    expected = request.session.get(_SESSION_KEY)
    if not expected or not secrets.compare_digest(expected, token):
        raise HTTPException(
            status_code=403,
            detail="Token CSRF inválido. Recargá la página e intentá de nuevo.",
        )


def csrf_input(request: Request) -> Markup:
    """Jinja2 global: renders a hidden CSRF input field."""
    token = get_csrf_token(request)
    return Markup(f'<input type="hidden" name="csrf_token" value="{token}">')


async def csrf_protect(request: Request, csrf_token: str = Form("")):
    """FastAPI Depends: validates CSRF token on POST endpoints."""
    validate_csrf(request, csrf_token)
