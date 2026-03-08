import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..auth import get_current_user
from ..csrf import csrf_protect
from ..db import get_db, get_user_settings, rows_as_dicts
from ..services import compute_quote_totals, days_since

router = APIRouter()

PAGE_SIZE = 20


def _t(request: Request):
    return request.app.state.templates


@router.get("/quotes", response_class=HTMLResponse)
async def quotes_page(request: Request, page: int = 1):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    offset = (page - 1) * PAGE_SIZE
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM quotes WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
        quotes = rows_as_dicts(conn.execute(
            "SELECT * FROM quotes WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user["id"], PAGE_SIZE, offset)).fetchall())
        for q in quotes:
            row = conn.execute(
                "SELECT SUM(quantity * unit_price) as total, COUNT(*) as cnt FROM quote_items WHERE quote_id = ?",
                (q["id"],)).fetchone()
            q["total"] = round(row["total"] or 0, 2)
            q["item_count"] = row["cnt"] or 0
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return _t(request).TemplateResponse(request, "quotes.html", {
        "active_tab": "quotes", "current_user": user, "quotes": quotes,
        "page": page, "pages": pages, "total": total,
    })


@router.post("/quotes/add")
async def add_quote(
    request: Request,
    _csrf: None = Depends(csrf_protect),
    client_name: str = Form(...),
    client_id: Optional[int] = Form(None),
    notes: str = Form(""),
    expires_at: str = Form(""),
    discount_pct: float = Form(0),
    surcharge_pct: float = Form(0),
    terms: str = Form(""),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    settings = get_user_settings(user["id"])
    effective_terms = terms.strip() or settings.get("terms_default", "")
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO quotes (user_id, client_id, client_name, notes, status, expires_at, "
            "discount_pct, surcharge_pct, terms, created_at) VALUES (?,?,?,?,'borrador',?,?,?,?,?)",
            (user["id"], client_id or None, client_name.strip(), notes.strip(),
             expires_at or None, discount_pct, surcharge_pct, effective_terms,
             datetime.now().strftime("%d/%m/%Y %H:%M")),
        )
        new_id = cursor.lastrowid
    return RedirectResponse(f"/quotes/{new_id}", status_code=303)


@router.get("/quotes/{quote_id}", response_class=HTMLResponse)
async def quote_detail(request: Request, quote_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        quote = conn.execute(
            "SELECT * FROM quotes WHERE id = ? AND user_id = ?", (quote_id, user["id"])).fetchone()
        if not quote:
            return RedirectResponse("/quotes", status_code=303)
        items = rows_as_dicts(conn.execute(
            "SELECT * FROM quote_items WHERE quote_id = ? ORDER BY id", (quote_id,)).fetchall())
        clients = rows_as_dicts(conn.execute(
            "SELECT id, name FROM clients WHERE user_id = ? ORDER BY name", (user["id"],)).fetchall())
    quote = dict(quote)
    totals = compute_quote_totals(items, quote.get("discount_pct", 0), quote.get("surcharge_pct", 0))
    settings = get_user_settings(user["id"])
    public_url = None
    if quote.get("public_token"):
        public_url = f"{request.base_url}p/{quote['public_token']}"
    days_sent = days_since(quote["created_at"]) if quote["status"] == "enviado" else None
    return _t(request).TemplateResponse(request, "quote_detail.html", {
        "active_tab": "quotes", "current_user": user, "quote": quote, "items": items,
        "totals": totals, "settings": settings, "clients": clients,
        "public_url": public_url, "days_sent": days_sent,
    })


@router.post("/quotes/{quote_id}/add-item")
async def add_quote_item(
    request: Request,
    quote_id: int,
    _csrf: None = Depends(csrf_protect),
    description: str = Form(...),
    quantity: int = Form(...),
    unit_price: float = Form(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        quote = conn.execute(
            "SELECT id FROM quotes WHERE id = ? AND user_id = ?", (quote_id, user["id"])).fetchone()
        if quote:
            conn.execute(
                "INSERT INTO quote_items (quote_id, description, quantity, unit_price) VALUES (?, ?, ?, ?)",
                (quote_id, description.strip(), quantity, unit_price),
            )
    return RedirectResponse(f"/quotes/{quote_id}", status_code=303)


@router.post("/quotes/{quote_id}/delete-item/{item_id}")
async def delete_quote_item(
    request: Request,
    quote_id: int,
    item_id: int,
    _csrf: None = Depends(csrf_protect),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        quote = conn.execute(
            "SELECT id FROM quotes WHERE id = ? AND user_id = ?", (quote_id, user["id"])).fetchone()
        if quote:
            conn.execute("DELETE FROM quote_items WHERE id = ? AND quote_id = ?", (item_id, quote_id))
    return RedirectResponse(f"/quotes/{quote_id}", status_code=303)


@router.post("/quotes/{quote_id}/update-status")
async def update_quote_status(
    request: Request,
    quote_id: int,
    _csrf: None = Depends(csrf_protect),
    status: str = Form(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if status not in ("borrador", "enviado", "aprobado", "rechazado"):
        return RedirectResponse(f"/quotes/{quote_id}", status_code=303)
    approved_at = datetime.now().strftime("%d/%m/%Y %H:%M") if status == "aprobado" else None
    with get_db() as conn:
        if approved_at:
            conn.execute("UPDATE quotes SET status=?, approved_at=? WHERE id=? AND user_id=?",
                         (status, approved_at, quote_id, user["id"]))
        else:
            conn.execute("UPDATE quotes SET status=? WHERE id=? AND user_id=?",
                         (status, quote_id, user["id"]))
    return RedirectResponse(f"/quotes/{quote_id}", status_code=303)


@router.post("/quotes/{quote_id}/update-settings")
async def update_quote_settings(
    request: Request,
    quote_id: int,
    _csrf: None = Depends(csrf_protect),
    client_name: str = Form(...),
    client_id: Optional[int] = Form(None),
    notes: str = Form(""),
    expires_at: str = Form(""),
    discount_pct: float = Form(0),
    surcharge_pct: float = Form(0),
    terms: str = Form(""),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute(
            "UPDATE quotes SET client_name=?, client_id=?, notes=?, expires_at=?, "
            "discount_pct=?, surcharge_pct=?, terms=? WHERE id=? AND user_id=?",
            (client_name.strip(), client_id or None, notes.strip(), expires_at or None,
             discount_pct, surcharge_pct, terms.strip(), quote_id, user["id"]))
    return RedirectResponse(f"/quotes/{quote_id}", status_code=303)


@router.post("/quotes/{quote_id}/generate-token")
async def generate_quote_token(
    request: Request,
    quote_id: int,
    _csrf: None = Depends(csrf_protect),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    token = secrets.token_urlsafe(16)
    with get_db() as conn:
        conn.execute("UPDATE quotes SET public_token=? WHERE id=? AND user_id=?",
                     (token, quote_id, user["id"]))
    return RedirectResponse(f"/quotes/{quote_id}", status_code=303)


@router.post("/quotes/{quote_id}/revoke-token")
async def revoke_quote_token(
    request: Request,
    quote_id: int,
    _csrf: None = Depends(csrf_protect),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("UPDATE quotes SET public_token=NULL WHERE id=? AND user_id=?",
                     (quote_id, user["id"]))
    return RedirectResponse(f"/quotes/{quote_id}", status_code=303)


@router.post("/quotes/delete/{quote_id}")
async def delete_quote(
    request: Request,
    quote_id: int,
    _csrf: None = Depends(csrf_protect),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM quotes WHERE id = ? AND user_id = ?", (quote_id, user["id"]))
    return RedirectResponse("/quotes", status_code=303)
