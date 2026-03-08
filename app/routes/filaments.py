from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_current_user
from ..db import get_db, rows_as_dicts

router = APIRouter()
templates: Jinja2Templates = None  # injected by create_app


@router.get("/filaments", response_class=HTMLResponse)
async def filaments_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        filaments = rows_as_dicts(conn.execute(
            "SELECT * FROM filaments WHERE user_id = ? ORDER BY id DESC", (user["id"],)).fetchall())
    return templates.TemplateResponse("filaments.html", {
        "request": request, "active_tab": "filaments",
        "current_user": user, "filaments": filaments,
    })


@router.post("/filaments/add")
async def add_filament(
    request: Request,
    brand: str = Form(...),
    material: str = Form(...),
    color: str = Form(""),
    weight_total_g: float = Form(...),
    weight_remaining_g: Optional[float] = Form(None),
    price_per_kg: float = Form(...),
    low_stock_alert_g: float = Form(100),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    remaining = weight_remaining_g if weight_remaining_g is not None else weight_total_g
    with get_db() as conn:
        conn.execute(
            "INSERT INTO filaments (user_id, brand, material, color, weight_total_g, weight_remaining_g, "
            "price_per_kg, low_stock_alert_g, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], brand.strip(), material.strip(), color.strip(),
             weight_total_g, remaining, price_per_kg, low_stock_alert_g,
             datetime.now().strftime("%d/%m/%Y %H:%M")),
        )
    return RedirectResponse("/filaments", status_code=303)


@router.post("/filaments/use/{filament_id}")
async def use_filament(request: Request, filament_id: int, used_g: float = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        row = conn.execute(
            "SELECT weight_remaining_g FROM filaments WHERE id = ? AND user_id = ?",
            (filament_id, user["id"])).fetchone()
        if row:
            new_remaining = max(0, row["weight_remaining_g"] - used_g)
            conn.execute("UPDATE filaments SET weight_remaining_g = ? WHERE id = ?",
                         (new_remaining, filament_id))
    return RedirectResponse("/filaments", status_code=303)


@router.post("/filaments/delete/{filament_id}")
async def delete_filament(request: Request, filament_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM filaments WHERE id = ? AND user_id = ?", (filament_id, user["id"]))
    return RedirectResponse("/filaments", status_code=303)


@router.post("/filaments/update-price/{filament_id}")
async def update_filament_price(request: Request, filament_id: int, price_per_kg: float = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("UPDATE filaments SET price_per_kg=? WHERE id=? AND user_id=?",
                     (price_per_kg, filament_id, user["id"]))
    return RedirectResponse("/filaments", status_code=303)
