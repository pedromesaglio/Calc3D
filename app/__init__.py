import os
import logging
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .csrf import csrf_input
from .db import get_secret_key, init_db
from .services import days_since
from .routes import auth, calculator, catalog, clients, dashboard, filaments, public, quotes, settings, subscriptions
from .middleware import RateLimitMiddleware, SubscriptionStatusMiddleware
from .error_handlers import register_error_handlers
from .config import Config

logger = logging.getLogger(__name__)


def create_app(db_path: str | None = None) -> FastAPI:
    """Application factory. Pass db_path for tests."""
    import app.db as db_module

    if db_path is not None:
        db_module.DB_FILE = db_path  # type: ignore[assignment]

    # Validar configuración en producción
    if Config.IS_PRODUCTION:
        try:
            Config.validate()
            logger.info("Configuration validated successfully")
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

    init_db(db_path)

    fastapi_app = FastAPI(
        title="Calc3D - Calculadora de Impresión 3D",
        version="2.0.0",
        description="Sistema profesional de cálculo de costos para impresión 3D con suscripciones",
    )

    templates = Jinja2Templates(directory="templates")
    templates.env.globals["days_since"] = days_since
    templates.env.globals["max"] = max
    templates.env.globals["min"] = min
    templates.env.globals["csrf_input"] = csrf_input

    fastapi_app.state.templates = templates

    # IMPORTANTE: Los middlewares se ejecutan en orden INVERSO
    # El último agregado es el primero en ejecutarse

    # Subscription status middleware (se ejecuta último)
    fastapi_app.add_middleware(SubscriptionStatusMiddleware)

    # Rate limiting middleware (solo en producción)
    if Config.IS_PRODUCTION:
        fastapi_app.add_middleware(
            RateLimitMiddleware,
            max_requests_per_minute=Config.RATE_LIMIT_PER_MINUTE,
            max_requests_per_hour=Config.RATE_LIMIT_PER_HOUR,
        )
        logger.info("Rate limiting enabled for production")

    # Session middleware (debe agregarse último para ejecutarse primero)
    fastapi_app.add_middleware(
        SessionMiddleware,
        secret_key=get_secret_key(db_path),
        max_age=60 * 60 * 24 * 30,
    )

    # Registrar error handlers
    register_error_handlers(fastapi_app)

    # Registrar routers
    for mod in (auth, calculator, catalog, clients, dashboard, filaments, public, quotes, settings, subscriptions):
        fastapi_app.include_router(mod.router)

    logger.info(f"Calc3D initialized successfully (Environment: {Config.ENVIRONMENT})")

    return fastapi_app
