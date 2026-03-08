from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..auth import get_current_user
from ..csrf import csrf_protect
from ..db import get_db, rows_as_dicts

router = APIRouter()

PAGE_SIZE = 12


def _t(request: Request):
    return request.app.state.templates


@router.get("/filaments", response_class=HTMLResponse)
async def filaments_page(request: Request, page: int = 1):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    offset = (page - 1) * PAGE_SIZE
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM filaments WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
        filaments = rows_as_dicts(conn.execute(
            "SELECT * FROM filaments WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user["id"], PAGE_SIZE, offset)).fetchall())
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return _t(request).TemplateResponse(request, "filaments.html", {
        "active_tab": "filaments", "current_user": user, "filaments": filaments,
        "page": page, "pages": pages, "total": total,
    })


@router.post("/filaments/add")
async def add_filament(
    request: Request,
    _csrf: None = Depends(csrf_protect),
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


@router.post("/filaments/edit/{filament_id}")
async def edit_filament(
    request: Request,
    filament_id: int,
    _csrf: None = Depends(csrf_protect),
    brand: str = Form(...),
    material: str = Form(...),
    color: str = Form(""),
    weight_total_g: float = Form(...),
    weight_remaining_g: float = Form(...),
    price_per_kg: float = Form(...),
    low_stock_alert_g: float = Form(100),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute(
            "UPDATE filaments SET brand=?, material=?, color=?, weight_total_g=?, "
            "weight_remaining_g=?, price_per_kg=?, low_stock_alert_g=? WHERE id=? AND user_id=?",
            (brand.strip(), material.strip(), color.strip(),
             weight_total_g, weight_remaining_g, price_per_kg, low_stock_alert_g,
             filament_id, user["id"]),
        )
    return RedirectResponse("/filaments", status_code=303)


@router.post("/filaments/use/{filament_id}")
async def use_filament(
    request: Request,
    filament_id: int,
    _csrf: None = Depends(csrf_protect),
    used_g: float = Form(...),
):
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
async def delete_filament(
    request: Request,
    filament_id: int,
    _csrf: None = Depends(csrf_protect),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM filaments WHERE id = ? AND user_id = ?", (filament_id, user["id"]))
    return RedirectResponse("/filaments", status_code=303)


@router.post("/filaments/update-price/{filament_id}")
async def update_filament_price(
    request: Request,
    filament_id: int,
    _csrf: None = Depends(csrf_protect),
    price_per_kg: float = Form(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("UPDATE filaments SET price_per_kg=? WHERE id=? AND user_id=?",
                     (price_per_kg, filament_id, user["id"]))
    return RedirectResponse("/filaments", status_code=303)
