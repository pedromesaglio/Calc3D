from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..auth import get_current_user
from ..csrf import csrf_protect
from ..db import get_db, rows_as_dicts

router = APIRouter()

PAGE_SIZE = 24


def _t(request: Request):
    return request.app.state.templates


@router.get("/catalog", response_class=HTMLResponse)
async def catalog_page(request: Request, page: int = 1):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    offset = (page - 1) * PAGE_SIZE
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM pieces WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
        pieces = rows_as_dicts(conn.execute(
            "SELECT * FROM pieces WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user["id"], PAGE_SIZE, offset)).fetchall())
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return _t(request).TemplateResponse(request, "catalog.html", {
        "active_tab": "catalog", "current_user": user, "pieces": pieces,
        "page": page, "pages": pages, "total": total,
    })


@router.post("/catalog/add")
async def add_piece(
    request: Request,
    _csrf: None = Depends(csrf_protect),
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


@router.post("/catalog/edit/{piece_id}")
async def edit_piece(
    request: Request,
    piece_id: int,
    _csrf: None = Depends(csrf_protect),
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
            "UPDATE pieces SET name=?, description=?, material=?, filament_weight=?, "
            "print_time=?, base_cost=?, selling_price=?, notes=? WHERE id=? AND user_id=?",
            (name.strip(), description.strip(), material.strip(),
             filament_weight, print_time, base_cost, selling_price,
             notes.strip(), piece_id, user["id"]),
        )
    return RedirectResponse("/catalog", status_code=303)


@router.post("/catalog/delete/{piece_id}")
async def delete_piece(
    request: Request,
    piece_id: int,
    _csrf: None = Depends(csrf_protect),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM pieces WHERE id = ? AND user_id = ?", (piece_id, user["id"]))
    return RedirectResponse("/catalog", status_code=303)
