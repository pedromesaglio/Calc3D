from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .db import DB_FILE, get_secret_key, init_db
from .services import days_since
from . import routes as route_modules
from .routes import auth, calculator, catalog, clients, dashboard, filaments, public, quotes, settings


def create_app(db_path: str | None = None) -> FastAPI:
    """Application factory. Pass db_path=':memory:' for tests."""
    import app.db as db_module

    if db_path is not None:
        db_module.DB_FILE = db_path  # type: ignore[assignment]

    init_db(db_path)

    app = FastAPI(title="Calc3D - Calculadora de Impresión 3D")
    templates = Jinja2Templates(directory="templates")
    templates.env.globals["days_since"] = days_since
    templates.env.globals["max"] = max
    templates.env.globals["min"] = min

    app.add_middleware(SessionMiddleware, secret_key=get_secret_key(db_path), max_age=60 * 60 * 24 * 30)

    # Inject templates into each route module
    for mod in (auth, calculator, catalog, clients, dashboard, filaments, public, quotes, settings):
        mod.templates = templates

    app.include_router(auth.router)
    app.include_router(calculator.router)
    app.include_router(catalog.router)
    app.include_router(clients.router)
    app.include_router(dashboard.router)
    app.include_router(filaments.router)
    app.include_router(public.router)
    app.include_router(quotes.router)
    app.include_router(settings.router)

    return app
