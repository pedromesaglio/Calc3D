import json
from datetime import datetime


def days_since(date_str: str) -> int:
    """Parse 'dd/mm/yyyy HH:MM' and return days elapsed."""
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M")
        return (datetime.now() - dt).days
    except Exception:
        return 0


def compute_quote_totals(
    items: list[dict], discount_pct: float, surcharge_pct: float
) -> dict:
    subtotal = sum(i["quantity"] * i["unit_price"] for i in items)
    surcharge_amt = round(subtotal * (surcharge_pct or 0) / 100, 2)
    after_surcharge = subtotal + surcharge_amt
    discount_amt = round(after_surcharge * (discount_pct or 0) / 100, 2)
    total = round(after_surcharge - discount_amt, 2)
    return {
        "subtotal": round(subtotal, 2),
        "surcharge_amt": surcharge_amt,
        "discount_amt": discount_amt,
        "total": total,
    }


def build_chart_data(
    base_cost_per_unit: float,
    filament_cost: float,
    electricity_cost: float,
    depreciation_cost: float,
    other_costs: float,
    multiplier: float,
) -> dict:
    multipliers = [1, 2, 3, 4, 5]
    if multiplier not in multipliers:
        multipliers = sorted(set(multipliers + [multiplier]))
    labels_m = [f"×{m}" for m in multipliers]
    cost_base = filament_cost + electricity_cost + depreciation_cost + other_costs

    breakdown = {
        "labels": labels_m,
        "datasets": [
            {"label": "Filamento",    "data": [round(filament_cost,     4)] * len(multipliers), "backgroundColor": "#94a3b8", "borderRadius": 4},
            {"label": "Electricidad", "data": [round(electricity_cost,  4)] * len(multipliers), "backgroundColor": "#6366f1", "borderRadius": 4},
            {"label": "Depreciación", "data": [round(depreciation_cost, 4)] * len(multipliers), "backgroundColor": "#8b5cf6", "borderRadius": 4},
            {"label": "Otros",        "data": [round(other_costs,       4)] * len(multipliers), "backgroundColor": "#f59e0b", "borderRadius": 4},
            {"label": "Ganancia",     "data": [round((m - 1) * cost_base, 4) for m in multipliers], "backgroundColor": "#10b981", "borderRadius": 4},
        ],
    }

    quantities = list(range(1, 21))
    rev_colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]

    cost_line = {
        "label": "Costo base",
        "data": [round(cost_base * q, 2) for q in quantities],
        "borderColor": "#94a3b8",
        "backgroundColor": "transparent",
        "borderDash": [6, 4],
        "borderWidth": 2,
        "tension": 0,
        "fill": False,
        "pointRadius": 0,
        "pointHoverRadius": 4,
        "order": 99,
    }
    revenue_lines = [
        {
            "label": f"Ingreso ×{m}",
            "data": [round(cost_base * m * q, 2) for q in quantities],
            "borderColor": rev_colors[i % len(rev_colors)],
            "backgroundColor": rev_colors[i % len(rev_colors)] + "15",
            "tension": 0.2,
            "fill": False,
            "borderWidth": 2,
            "pointRadius": 0,
            "pointHoverRadius": 5,
            "order": i,
        }
        for i, m in enumerate(multipliers)
    ]
    profit = {"labels": quantities, "datasets": [cost_line] + revenue_lines}
    return {"breakdown": json.dumps(breakdown), "profit": json.dumps(profit)}
