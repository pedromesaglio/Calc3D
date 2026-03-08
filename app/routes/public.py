from datetime import date, datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..db import get_db, get_user_settings, rows_as_dicts
from ..services import compute_quote_totals

router = APIRouter()
templates: Jinja2Templates = None  # injected by create_app


@router.get("/p/{token}", response_class=HTMLResponse)
async def public_quote_view(request: Request, token: str):
    with get_db() as conn:
        quote = conn.execute("SELECT * FROM quotes WHERE public_token = ?", (token,)).fetchone()
        if not quote:
            return HTMLResponse("<h2>Presupuesto no encontrado o link expirado.</h2>", status_code=404)
        quote = dict(quote)
        items = rows_as_dicts(conn.execute(
            "SELECT * FROM quote_items WHERE quote_id = ? ORDER BY id", (quote["id"],)).fetchall())
        settings = get_user_settings(quote["user_id"])
    totals = compute_quote_totals(items, quote.get("discount_pct", 0), quote.get("surcharge_pct", 0))
    expired = False
    if quote.get("expires_at"):
        try:
            exp = datetime.strptime(quote["expires_at"], "%Y-%m-%d").date()
            expired = date.today() > exp
        except Exception:
            pass
    return templates.TemplateResponse("public_quote.html", {
        "request": request, "quote": quote, "items": items,
        "totals": totals, "settings": settings, "expired": expired, "token": token,
    })


@router.post("/p/{token}/approve")
async def public_quote_approve(request: Request, token: str):
    with get_db() as conn:
        quote = conn.execute(
            "SELECT id, status, expires_at FROM quotes WHERE public_token = ?", (token,)
        ).fetchone()
        if not quote or quote["status"] in ("aprobado", "rechazado"):
            return RedirectResponse(f"/p/{token}", status_code=303)
        if quote["expires_at"]:
            try:
                exp = datetime.strptime(quote["expires_at"], "%Y-%m-%d").date()
                if date.today() > exp:
                    return RedirectResponse(f"/p/{token}", status_code=303)
            except Exception:
                pass
        conn.execute(
            "UPDATE quotes SET status='aprobado', approved_at=? WHERE id=?",
            (datetime.now().strftime("%d/%m/%Y %H:%M"), quote["id"]))
    return RedirectResponse(f"/p/{token}", status_code=303)
