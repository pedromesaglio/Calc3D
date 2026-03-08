import sqlite3
from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_current_user, hash_password, verify_password
from ..db import get_db

router = APIRouter()
templates: Jinja2Templates = None  # injected by create_app


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = "", tab: str = "login"):
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "tab": tab})


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuario o contraseña incorrectos.", "tab": "login"},
            status_code=401,
        )
    request.session["user_id"] = row["id"]
    return RedirectResponse("/", status_code=303)


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
):
    username = username.strip()
    error = None
    if len(username) < 3:
        error = "El nombre de usuario debe tener al menos 3 caracteres."
    elif len(password) < 6:
        error = "La contraseña debe tener al menos 6 caracteres."
    elif password != password2:
        error = "Las contraseñas no coinciden."

    if error:
        return templates.TemplateResponse("login.html", {"request": request, "error": error, "tab": "register"})

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, hash_password(password), datetime.now().strftime("%d/%m/%Y %H:%M")),
            )
    except sqlite3.IntegrityError:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Ese nombre de usuario ya está en uso.", "tab": "register"},
        )

    return RedirectResponse("/login?tab=login", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
