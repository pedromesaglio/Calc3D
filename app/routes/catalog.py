from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_current_user
from ..db import get_db, rows_as_dicts

router = APIRouter()
templates: Jinja2Templates = None  # injected by create_app


@router.get("/catalog", response_class=HTMLResponse)
async def catalog_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        pieces = rows_as_dicts(conn.execute(
            "SELECT * FROM pieces WHERE user_id = ? ORDER BY id DESC", (user["id"],)).fetchall())
    return templates.TemplateResponse("catalog.html", {
        "request": request, "active_tab": "catalog",
        "current_user": user, "pieces": pieces,
    })


@router.post("/catalog/add")
async def add_piece(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    material: str = Form(""),
    filament_weight: Optional[float] = Form(None),
    print_time: Optional[float] = Form(None),
    base_cost: Optional[float] = Form(None),
    selling_price: Optional[float] = Form(None),
    notes: str = Form(""),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO pieces (user_id, name, description, material, filament_weight, print_time, "
            "base_cost, selling_price, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], name.strip(), description.strip(), material.strip(),
             filament_weight, print_time, base_cost, selling_price,
             notes.strip(), datetime.now().strftime("%d/%m/%Y %H:%M")),
        )
    return RedirectResponse("/catalog", status_code=303)


@router.post("/catalog/delete/{piece_id}")
async def delete_piece(request: Request, piece_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM pieces WHERE id = ? AND user_id = ?", (piece_id, user["id"]))
    return RedirectResponse("/catalog", status_code=303)
