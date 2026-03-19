"""
Configuración de la aplicación
Carga variables de entorno y proporciona configuración centralizada
"""
import os
import logging
from pathlib import Path

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # python-dotenv no instalado, usar solo variables de entorno del sistema
    pass


class Config:
    """Configuración centralizada de la aplicación"""

    # Entorno
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    IS_PRODUCTION = ENVIRONMENT == "production"

    # Base de datos
    DATABASE_PATH = os.getenv("DATABASE_PATH", "calc3d.db")

    # URLs
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

    # Stripe
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO")
    STRIPE_PRICE_ID_BUSINESS = os.getenv("STRIPE_PRICE_ID_BUSINESS")

    # Mercado Pago
    MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    MERCADOPAGO_PUBLIC_KEY = os.getenv("MERCADOPAGO_PUBLIC_KEY")
    MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
    MERCADOPAGO_PLAN_ID_PRO = os.getenv("MERCADOPAGO_PLAN_ID_PRO")
    MERCADOPAGO_PLAN_ID_BUSINESS = os.getenv("MERCADOPAGO_PLAN_ID_BUSINESS")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

    # Seguridad y autenticación
    PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "260000"))  # OWASP recomienda 260k para SHA-256
    SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))  # Duración de sesiones

    # Suscripciones
    TRIAL_PERIOD_DAYS = int(os.getenv("TRIAL_PERIOD_DAYS", "14"))  # Días de prueba gratuita
    BILLING_CYCLE_DAYS = int(os.getenv("BILLING_CYCLE_DAYS", "30"))  # Ciclo de facturación
    USAGE_RESET_PERIOD_DAYS = int(os.getenv("USAGE_RESET_PERIOD_DAYS", "30"))  # Reset de límites de uso

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "calc3d.log")

    @classmethod
    def setup_logging(cls):
        """Configura el sistema de logging"""
        log_level = getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO)

        # Formato de logs
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"

        # Configuración de handlers
        handlers = [
            logging.StreamHandler(),  # Consola
        ]

        # En producción, agregar archivo de logs
        if cls.IS_PRODUCTION and cls.LOG_FILE:
            handlers.append(
                logging.FileHandler(cls.LOG_FILE, encoding="utf-8")
            )

        # Configurar logging
        logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt=date_format,
            handlers=handlers,
            force=True,
        )

        # Reducir verbosidad de librerías externas
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    @classmethod
    def validate(cls):
        """Valida que las configuraciones críticas estén presentes"""
        errors = []

        # En producción, validar configuraciones de pago
        if cls.IS_PRODUCTION:
            if not cls.STRIPE_SECRET_KEY and not cls.MERCADOPAGO_ACCESS_TOKEN:
                errors.append(
                    "PRODUCCIÓN: Se requiere al menos Stripe o Mercado Pago configurado"
                )

            if cls.STRIPE_SECRET_KEY:
                if not cls.STRIPE_WEBHOOK_SECRET:
                    errors.append("STRIPE_WEBHOOK_SECRET no configurado")
                if not cls.STRIPE_PRICE_ID_PRO or not cls.STRIPE_PRICE_ID_BUSINESS:
                    errors.append("IDs de precios de Stripe no configurados")

            if cls.MERCADOPAGO_ACCESS_TOKEN:
                if not cls.MERCADOPAGO_WEBHOOK_SECRET:
                    errors.append("MERCADOPAGO_WEBHOOK_SECRET no configurado")

        if errors:
            error_msg = "\n".join(["❌ " + e for e in errors])
            raise ValueError(f"Errores de configuración:\n{error_msg}")

    @classmethod
    def get_info(cls) -> dict:
        """Retorna información de configuración (sin exponer secretos)"""
        return {
            "environment": cls.ENVIRONMENT,
            "is_production": cls.IS_PRODUCTION,
            "database_path": cls.DATABASE_PATH,
            "base_url": cls.BASE_URL,
            "stripe_configured": bool(cls.STRIPE_SECRET_KEY),
            "mercadopago_configured": bool(cls.MERCADOPAGO_ACCESS_TOKEN),
            "rate_limit_per_minute": cls.RATE_LIMIT_PER_MINUTE,
            "rate_limit_per_hour": cls.RATE_LIMIT_PER_HOUR,
            "log_level": cls.LOG_LEVEL,
        }


# Configurar logging al importar
Config.setup_logging()

# Instancia global de configuración
config = Config()
