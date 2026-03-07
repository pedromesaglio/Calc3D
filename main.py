from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
from datetime import datetime
from pathlib import Path
import hashlib, secrets, sqlite3, json

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Calc3D - Calculadora de Impresión 3D")
templates = Jinja2Templates(directory="templates")
DB_FILE = Path("calc3d.db")


# ── Database ──────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS printers (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name                  TEXT NOT NULL,
                watts                 REAL NOT NULL,
                purchase_price        REAL NOT NULL,
                lifespan_years        REAL NOT NULL,
                lifespan_hours        REAL NOT NULL,
                depreciation_per_hour REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS history (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                timestamp             TEXT NOT NULL,
                printer_id            INTEGER,
                printer_name          TEXT,
                filament_weight       REAL,
                filament_price_kg     REAL,
                print_time            REAL,
                printer_watts         REAL,
                electricity_rate      REAL,
                other_costs           REAL,
                quantity              INTEGER,
                multiplier            REAL,
                depr_per_hour         REAL,
                filament_cost         REAL,
                electricity_cost      REAL,
                depreciation_cost     REAL,
                base_cost_per_unit    REAL,
                total_base_cost       REAL,
                selling_price_per_unit REAL,
                total_selling_price   REAL,
                profit                REAL,
                margin_pct            REAL
            );
        """)
        # Migrate: add user_id to legacy tables (no-op if already present)
        for table in ("printers", "history"):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")
            except sqlite3.OperationalError:
                pass


def get_secret_key() -> str:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM config WHERE key='secret_key'").fetchone()
        if row:
            return row[0]
        key = secrets.token_hex(32)
        conn.execute("INSERT INTO config (key, value) VALUES ('secret_key', ?)", (key,))
        return key


init_db()
app.add_middleware(SessionMiddleware, secret_key=get_secret_key(), max_age=60 * 60 * 24 * 30)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000).hex()
    return f"{salt}${h}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$")
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000).hex()
        return secrets.compare_digest(check, h)
    except Exception:
        return False


def get_current_user(request: Request) -> dict | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    with get_db() as conn:
        row = conn.execute("SELECT id, username, created_at FROM users WHERE id = ?", (uid,)).fetchone()
        return dict(row) if row else None


def require_user(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise _redirect_to_login()
    return user


def _redirect_to_login():
    from fastapi import HTTPException
    # Using a trick: return a redirect response as an exception-like
    return Exception("not_authed")


# ── Context helper ────────────────────────────────────────────────────────────

def rows_as_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _ctx(user: dict, extra: dict = {}) -> dict:
    uid = user["id"]
    with get_db() as conn:
        printers = rows_as_dicts(conn.execute(
            "SELECT * FROM printers WHERE user_id = ? ORDER BY id", (uid,)).fetchall())
        history = rows_as_dicts(conn.execute(
            "SELECT * FROM history WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall())
    return {"printers": printers, "history": history, "current_user": user, **extra}


# ── Chart data ────────────────────────────────────────────────────────────────

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
            {"label": "Filamento",    "data": [round(filament_cost,    4)] * len(multipliers), "backgroundColor": "#94a3b8", "borderRadius": 4},
            {"label": "Electricidad", "data": [round(electricity_cost, 4)] * len(multipliers), "backgroundColor": "#6366f1", "borderRadius": 4},
            {"label": "Depreciación", "data": [round(depreciation_cost,4)] * len(multipliers), "backgroundColor": "#8b5cf6", "borderRadius": 4},
            {"label": "Otros",        "data": [round(other_costs,      4)] * len(multipliers), "backgroundColor": "#f59e0b", "borderRadius": 4},
            {"label": "Ganancia",     "data": [round((m - 1) * cost_base, 4) for m in multipliers], "backgroundColor": "#10b981", "borderRadius": 4},
        ],
    }

    quantities = list(range(1, 21))
    rev_colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]

    # Línea de referencia: costo base total
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
    # Líneas de ingreso por multiplicador
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


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = "", tab: str = "login"):
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "tab": tab})


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip(),)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuario o contraseña incorrectos.", "tab": "login"},
            status_code=401,
        )
    request.session["user_id"] = row["id"]
    return RedirectResponse("/", status_code=303)


@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
):
    username = username.strip()
    error = None
    if len(username) < 3:
        error = "El nombre de usuario debe tener al menos 3 caracteres."
    elif len(password) < 6:
        error = "La contraseña debe tener al menos 6 caracteres."
    elif password != password2:
        error = "Las contraseñas no coinciden."

    if error:
        return templates.TemplateResponse("login.html", {"request": request, "error": error, "tab": "register"})

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, hash_password(password), datetime.now().strftime("%d/%m/%Y %H:%M")),
            )
    except sqlite3.IntegrityError:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Ese nombre de usuario ya está en uso.", "tab": "register"},
        )

    return RedirectResponse("/login?tab=login", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ── Main app routes ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, **_ctx(user)})


@app.post("/printers/add")
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


@app.post("/printers/delete/{printer_id}")
async def delete_printer(request: Request, printer_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM printers WHERE id = ? AND user_id = ?", (printer_id, user["id"]))
    return RedirectResponse("/", status_code=303)


@app.post("/calculate", response_class=HTMLResponse)
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
            "last_result": last_result,
            "chart_breakdown": charts["breakdown"],
            "chart_profit": charts["profit"],
            **_ctx(user),
        },
    )


@app.post("/clear-history")
async def clear_history(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    with get_db() as conn:
        conn.execute("DELETE FROM history WHERE user_id = ?", (user["id"],))
    return RedirectResponse("/", status_code=303)
