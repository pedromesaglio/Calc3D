import sqlite3
from pathlib import Path

DB_FILE: Path = Path("calc3d.db")


def get_db(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or str(DB_FILE)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def rows_as_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def init_db(db_path: str | None = None) -> None:
    with get_db(db_path) as conn:
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

            CREATE TABLE IF NOT EXISTS pieces (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name           TEXT NOT NULL,
                description    TEXT,
                material       TEXT,
                filament_weight REAL,
                print_time     REAL,
                base_cost      REAL,
                selling_price  REAL,
                notes          TEXT,
                created_at     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS filaments (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                brand               TEXT NOT NULL,
                material            TEXT NOT NULL,
                color               TEXT,
                weight_total_g      REAL NOT NULL,
                weight_remaining_g  REAL NOT NULL,
                price_per_kg        REAL NOT NULL,
                low_stock_alert_g   REAL NOT NULL DEFAULT 100,
                created_at          TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clients (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name       TEXT NOT NULL,
                email      TEXT,
                phone      TEXT,
                address    TEXT,
                notes      TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quotes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                client_id     INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                client_name   TEXT NOT NULL,
                notes         TEXT,
                status        TEXT NOT NULL DEFAULT 'borrador',
                expires_at    TEXT,
                discount_pct  REAL NOT NULL DEFAULT 0,
                surcharge_pct REAL NOT NULL DEFAULT 0,
                terms         TEXT,
                public_token  TEXT UNIQUE,
                approved_at   TEXT,
                created_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quote_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id    INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                quantity    INTEGER NOT NULL DEFAULT 1,
                unit_price  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                business_name    TEXT NOT NULL DEFAULT '',
                business_tagline TEXT NOT NULL DEFAULT '',
                business_address TEXT NOT NULL DEFAULT '',
                business_phone   TEXT NOT NULL DEFAULT '',
                business_email   TEXT NOT NULL DEFAULT '',
                currency         TEXT NOT NULL DEFAULT '$',
                terms_default    TEXT NOT NULL DEFAULT ''
            );
        """)
        # Migrations
        for table, col, definition in [
            ("printers", "user_id", "INTEGER"),
            ("history",  "user_id", "INTEGER"),
            ("quotes", "client_id",     "INTEGER"),
            ("quotes", "expires_at",    "TEXT"),
            ("quotes", "discount_pct",  "REAL NOT NULL DEFAULT 0"),
            ("quotes", "surcharge_pct", "REAL NOT NULL DEFAULT 0"),
            ("quotes", "terms",         "TEXT"),
            ("quotes", "public_token",  "TEXT"),
            ("quotes", "approved_at",   "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            except sqlite3.OperationalError:
                pass


def get_secret_key(db_path: str | None = None) -> str:
    import secrets
    with get_db(db_path) as conn:
        row = conn.execute("SELECT value FROM config WHERE key='secret_key'").fetchone()
        if row:
            return row[0]
        key = secrets.token_hex(32)
        conn.execute("INSERT INTO config (key, value) VALUES ('secret_key', ?)", (key,))
        return key


def get_user_settings(user_id: int, db_path: str | None = None) -> dict:
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return dict(row)
        return {
            "user_id": user_id, "business_name": "", "business_tagline": "",
            "business_address": "", "business_phone": "", "business_email": "",
            "currency": "$", "terms_default": "",
        }
