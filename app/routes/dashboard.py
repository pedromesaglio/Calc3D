import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..auth import get_current_user
from ..db import get_db, rows_as_dicts
from ..services import compute_quote_totals, days_since

router = APIRouter()


def _t(request: Request):
    return request.app.state.templates


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    uid = user["id"]
    with get_db() as conn:
        all_quotes = rows_as_dicts(conn.execute(
            "SELECT q.* FROM quotes q WHERE q.user_id = ? ORDER BY q.id DESC", (uid,)).fetchall())
        for q in all_quotes:
            items = rows_as_dicts(conn.execute(
                "SELECT quantity, unit_price FROM quote_items WHERE quote_id = ?",
                (q["id"],)).fetchall())
            q["total"] = compute_quote_totals(
                items, q.get("discount_pct", 0), q.get("surcharge_pct", 0))["total"]
            q["item_count"] = len(items)

        history = rows_as_dicts(conn.execute(
            "SELECT * FROM history WHERE user_id = ? ORDER BY id", (uid,)).fetchall())

        printers = rows_as_dicts(conn.execute(
            "SELECT * FROM printers WHERE user_id = ?", (uid,)).fetchall())
        for p in printers:
            hours = conn.execute(
                "SELECT COALESCE(SUM(print_time), 0) as h FROM history WHERE user_id=? AND printer_id=?",
                (uid, p["id"])).fetchone()["h"]
            p["hours_printed"] = round(hours, 1)
            p["pct_lifespan"] = round(hours / p["lifespan_hours"] * 100, 1) if p["lifespan_hours"] else 0
            p["cost_recovered"] = round(hours * p["depreciation_per_hour"], 2)
            p["cost_remaining"] = round(p["purchase_price"] - p["cost_recovered"], 2)

        pieces = rows_as_dicts(conn.execute(
            "SELECT * FROM pieces WHERE user_id=? AND base_cost > 0 AND selling_price > 0 "
            "ORDER BY (selling_price - base_cost) / selling_price DESC LIMIT 5",
            (uid,)).fetchall())
        for p in pieces:
            p["margin_pct"] = round(
                (p["selling_price"] - p["base_cost"]) / p["selling_price"] * 100, 1)

    total_quotes = len(all_quotes)
    sent_quotes = [q for q in all_quotes if q["status"] in ("enviado", "aprobado", "rechazado")]
    approved = [q for q in all_quotes if q["status"] == "aprobado"]
    rejected = [q for q in all_quotes if q["status"] == "rechazado"]
    conversion = round(len(approved) / len(sent_quotes) * 100, 1) if sent_quotes else 0
    revenue_total = round(sum(q["total"] for q in approved), 2)

    monthly: dict[str, float] = {}
    for i in range(5, -1, -1):
        m = (datetime.now().replace(day=1) - timedelta(days=i * 30))
        key = m.strftime("%Y-%m")
        monthly[key] = 0.0
    for q in approved:
        try:
            dt = datetime.strptime(q["created_at"], "%d/%m/%Y %H:%M")
            key = dt.strftime("%Y-%m")
            if key in monthly:
                monthly[key] += q["total"]
        except Exception:
            pass
    monthly_labels, monthly_values = [], []
    for k, v in monthly.items():
        try:
            monthly_labels.append(datetime.strptime(k, "%Y-%m").strftime("%b %Y"))
        except Exception:
            monthly_labels.append(k)
        monthly_values.append(round(v, 2))

    margins = [h["margin_pct"] for h in history if h.get("margin_pct") is not None]
    avg_margin = round(sum(margins) / len(margins), 1) if margins else 0

    pending_followup = [q for q in all_quotes
                        if q["status"] == "enviado" and days_since(q["created_at"]) >= 7]

    return _t(request).TemplateResponse(request, "dashboard.html", {
        "active_tab": "dashboard", "current_user": user,
        "total_quotes": total_quotes, "approved_count": len(approved),
        "rejected_count": len(rejected), "conversion": conversion,
        "revenue_total": revenue_total, "avg_margin": avg_margin,
        "printers": printers, "pieces": pieces,
        "pending_followup": pending_followup,
        "monthly_labels": json.dumps(monthly_labels),
        "monthly_values": json.dumps(monthly_values),
        "recent_quotes": all_quotes[:5],
    })
