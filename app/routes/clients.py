from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_current_user
from ..db import get_db, rows_as_dicts
from ..services import compute_quote_totals

router = APIRouter()
templates: Jinja2Templates = None  # injected by create_app


@router.get("/clients", response_class=HTMLResponse)
async def clients_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        clients = rows_as_dicts(conn.execute(
            "SELECT * FROM clients WHERE user_id = ? ORDER BY name", (user["id"],)).fetchall())
        for c in clients:
            row = conn.execute(
                "SELECT COUNT(*) as total, SUM(CASE WHEN status='aprobado' THEN 1 ELSE 0 END) as approved "
                "FROM quotes WHERE client_id = ?", (c["id"],)).fetchone()
            c["quote_count"] = row["total"] or 0
            c["approved_count"] = row["approved"] or 0
    return templates.TemplateResponse("clients.html", {
        "request": request, "active_tab": "clients",
        "current_user": user, "clients": clients,
    })


@router.post("/clients/add")
async def add_client(
    request: Request,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    notes: str = Form(""),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO clients (user_id, name, email, phone, address, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user["id"], name.strip(), email.strip(), phone.strip(),
             address.strip(), notes.strip(), datetime.now().strftime("%d/%m/%Y %H:%M")),
        )
    return RedirectResponse("/clients", status_code=303)


@router.get("/clients/{client_id}", response_class=HTMLResponse)
async def client_detail(request: Request, client_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        client = conn.execute(
            "SELECT * FROM clients WHERE id = ? AND user_id = ?", (client_id, user["id"])).fetchone()
        if not client:
            return RedirectResponse("/clients", status_code=303)
        quotes = rows_as_dicts(conn.execute(
            "SELECT * FROM quotes WHERE client_id = ? ORDER BY id DESC", (client_id,)).fetchall())
        for q in quotes:
            items = rows_as_dicts(conn.execute(
                "SELECT quantity, unit_price FROM quote_items WHERE quote_id = ?",
                (q["id"],)).fetchall())
            t = compute_quote_totals(items, q.get("discount_pct", 0), q.get("surcharge_pct", 0))
            q["total"] = t["total"]
            q["item_count"] = len(items)
    client = dict(client)
    total_quoted = sum(q["total"] for q in quotes)
    total_approved = sum(q["total"] for q in quotes if q["status"] == "aprobado")
    return templates.TemplateResponse("client_detail.html", {
        "request": request, "active_tab": "clients",
        "current_user": user, "client": client, "quotes": quotes,
        "total_quoted": round(total_quoted, 2), "total_approved": round(total_approved, 2),
    })


@router.post("/clients/delete/{client_id}")
async def delete_client(request: Request, client_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM clients WHERE id = ? AND user_id = ?", (client_id, user["id"]))
    return RedirectResponse("/clients", status_code=303)
