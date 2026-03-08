from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..auth import get_current_user
from ..db import get_db, rows_as_dicts
from ..services import build_chart_data

router = APIRouter()
templates: Jinja2Templates = None  # injected by create_app


def _ctx(user: dict, extra: dict = {}) -> dict:
    uid = user["id"]
    with get_db() as conn:
        printers = rows_as_dicts(conn.execute(
            "SELECT * FROM printers WHERE user_id = ? ORDER BY id", (uid,)).fetchall())
        history = rows_as_dicts(conn.execute(
            "SELECT * FROM history WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall())
    return {"printers": printers, "history": history, "current_user": user, **extra}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "active_tab": "calc", **_ctx(user)})


@router.post("/printers/add")
async def add_printer(
    request: Request,
    name: str = Form(...),
    watts: float = Form(...),
    purchase_price: float = Form(...),
    lifespan_years: float = Form(...),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    lifespan_hours = lifespan_years * 8760
    depr = round(purchase_price / lifespan_hours, 6) if lifespan_hours > 0 else 0.0
    with get_db() as conn:
        conn.execute(
            "INSERT INTO printers (user_id, name, watts, purchase_price, lifespan_years, lifespan_hours, depreciation_per_hour) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user["id"], name, watts, purchase_price, lifespan_years, round(lifespan_hours, 1), depr),
        )
    return RedirectResponse("/", status_code=303)


@router.post("/printers/delete/{printer_id}")
async def delete_printer(request: Request, printer_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM printers WHERE id = ? AND user_id = ?", (printer_id, user["id"]))
    return RedirectResponse("/", status_code=303)


@router.post("/calculate", response_class=HTMLResponse)
async def calculate(
    request: Request,
    filament_weight: float = Form(...),
    filament_price_kg: float = Form(...),
    print_time: float = Form(...),
    printer_watts: float = Form(...),
    electricity_rate: float = Form(...),
    other_costs: float = Form(0.0),
    quantity: int = Form(...),
    multiplier_preset: str = Form("2"),
    custom_multiplier: Optional[float] = Form(None),
    printer_id: Optional[int] = Form(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    multiplier = (
        custom_multiplier
        if multiplier_preset == "custom" and custom_multiplier
        else float(multiplier_preset)
    )

    selected_printer = None
    if printer_id:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM printers WHERE id = ? AND user_id = ?", (printer_id, user["id"])
            ).fetchone()
            if row:
                selected_printer = dict(row)

    printer_name  = selected_printer["name"] if selected_printer else None
    depr_per_hour = selected_printer["depreciation_per_hour"] if selected_printer else 0.0

    filament_cost     = (filament_weight / 1000.0) * filament_price_kg
    electricity_cost  = (printer_watts / 1000.0) * print_time * electricity_rate
    depreciation_cost = round(depr_per_hour * print_time, 6)
    base_cost_per_unit    = filament_cost + electricity_cost + depreciation_cost + other_costs
    total_base_cost       = base_cost_per_unit * quantity
    selling_price_per_unit = base_cost_per_unit * multiplier
    total_selling_price   = selling_price_per_unit * quantity
    profit     = total_selling_price - total_base_cost
    margin_pct = (profit / total_selling_price * 100) if total_selling_price else 0

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO history (
                user_id, timestamp, printer_id, printer_name,
                filament_weight, filament_price_kg, print_time, printer_watts,
                electricity_rate, other_costs, quantity, multiplier, depr_per_hour,
                filament_cost, electricity_cost, depreciation_cost,
                base_cost_per_unit, total_base_cost,
                selling_price_per_unit, total_selling_price, profit, margin_pct
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                user["id"],
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                printer_id, printer_name,
                filament_weight, filament_price_kg, print_time, printer_watts,
                electricity_rate, other_costs, quantity, multiplier, depr_per_hour,
                round(filament_cost, 4), round(electricity_cost, 4), round(depreciation_cost, 4),
                round(base_cost_per_unit, 4), round(total_base_cost, 4),
                round(selling_price_per_unit, 4), round(total_selling_price, 4),
                round(profit, 4), round(margin_pct, 1),
            ),
        )
        new_id = cursor.lastrowid

    last_result = {
        "id": new_id,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "printer_id": printer_id, "printer_name": printer_name,
        "filament_weight": filament_weight, "filament_price_kg": filament_price_kg,
        "print_time": print_time, "printer_watts": printer_watts,
        "electricity_rate": electricity_rate, "other_costs": other_costs,
        "quantity": quantity, "multiplier": multiplier, "depr_per_hour": depr_per_hour,
        "filament_cost": round(filament_cost, 4),
        "electricity_cost": round(electricity_cost, 4),
        "depreciation_cost": round(depreciation_cost, 4),
        "base_cost_per_unit": round(base_cost_per_unit, 4),
        "total_base_cost": round(total_base_cost, 4),
        "selling_price_per_unit": round(selling_price_per_unit, 4),
        "total_selling_price": round(total_selling_price, 4),
        "profit": round(profit, 4),
        "margin_pct": round(margin_pct, 1),
    }

    charts = build_chart_data(
        base_cost_per_unit, filament_cost, electricity_cost,
        depreciation_cost, other_costs, multiplier,
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "active_tab": "calc",
            "last_result": last_result,
            "chart_breakdown": charts["breakdown"],
            "chart_profit": charts["profit"],
            **_ctx(user),
        },
    )


@router.post("/clear-history")
async def clear_history(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM history WHERE user_id = ?", (user["id"],))
    return RedirectResponse("/", status_code=303)
