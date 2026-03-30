"""
Middleware para verificación de límites de uso, rate limiting y control de acceso
"""
import logging
import time
from typing import Callable
from fastapi import Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .subscriptions import check_limit, increment_usage, get_or_create_subscription, has_feature

logger = logging.getLogger(__name__)


async def check_usage_limit(
    request: Request,
    resource_type: str,
    redirect_to_pricing: bool = True
):
    """
    Middleware para verificar límites de uso

    Args:
        request: Request de FastAPI
        resource_type: Tipo de recurso ('calculations', 'quotes', 'clients', 'catalog_items')
        redirect_to_pricing: Si True, redirige a /pricing, si False retorna JSON error

    Returns:
        None si puede usar el recurso, RedirectResponse o JSONResponse si no puede
    """
    from .auth import get_current_user
    user = get_current_user(request)
    if not user:
        return None  # Si no hay usuario, dejamos que el auth handler se encargue

    can_use, error = check_limit(user["id"], resource_type)

    if not can_use:
        if redirect_to_pricing:
            # Para requests HTML, redirigir a pricing con mensaje de error
            import urllib.parse
            error_encoded = urllib.parse.quote(error)
            return RedirectResponse(
                f"/pricing?error={error_encoded}&resource={resource_type}",
                status_code=303
            )
        else:
            # Para requests API, retornar JSON
            return JSONResponse(
                {
                    "error": "Límite alcanzado",
                    "message": error,
                    "resource_type": resource_type,
                    "upgrade_url": "/pricing"
                },
                status_code=403
            )

    return None


def track_usage(user_id: int, resource_type: str, amount: int = 1):
    """
    Helper para incrementar el uso de un recurso

    Args:
        user_id: ID del usuario
        resource_type: Tipo de recurso
        amount: Cantidad a incrementar (default: 1)
    """
    increment_usage(user_id, resource_type, amount)


class UsageLimitMiddleware:
    """
    Middleware de clase para usar con FastAPI
    Ejemplo de uso en rutas específicas
    """
    def __init__(self, resource_type: str):
        self.resource_type = resource_type

    async def __call__(self, request: Request):
        return await check_usage_limit(request, self.resource_type)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware profesional de rate limiting por IP y usuario
    Previene abuso de la API con límites configurables
    """

    def __init__(
        self,
        app,
        max_requests_per_minute: int = 100,
        max_requests_per_hour: int = 1000,
    ):
        super().__init__(app)
        self.max_per_minute = max_requests_per_minute
        self.max_per_hour = max_requests_per_hour
        self.minute_counts = {}  # {key: [(timestamp, count), ...]}
        self.hour_counts = {}    # {key: [(timestamp, count), ...]}

    def _get_client_key(self, request: Request) -> str:
        """Obtiene una clave única para el cliente (IP + user_id si está logueado)"""
        client_ip = request.client.host if request.client else "unknown"
        user_id = request.session.get("user_id")
        return f"{client_ip}:{user_id}" if user_id else client_ip

    def _clean_old_entries(self, counts_dict: dict, window_seconds: int, now: float):
        """Limpia entradas antiguas del diccionario de contadores"""
        for key in list(counts_dict.keys()):
            counts_dict[key] = [
                (ts, count) for ts, count in counts_dict[key]
                if now - ts < window_seconds
            ]
            if not counts_dict[key]:
                del counts_dict[key]

    def _get_request_count(self, counts_dict: dict, key: str) -> int:
        """Obtiene el conteo total de requests para una clave"""
        return sum(count for _, count in counts_dict.get(key, []))

    async def dispatch(self, request: Request, call_next: Callable):
        """Aplica rate limiting por IP/usuario"""

        # Rutas exentas de rate limiting
        exempt_routes = ["/static/", "/webhooks/"]
        if any(request.url.path.startswith(route) for route in exempt_routes):
            return await call_next(request)

        client_key = self._get_client_key(request)
        now = time.time()

        # Limpiar entradas antiguas
        self._clean_old_entries(self.minute_counts, 60, now)
        self._clean_old_entries(self.hour_counts, 3600, now)

        # Verificar límites
        minute_count = self._get_request_count(self.minute_counts, client_key)
        hour_count = self._get_request_count(self.hour_counts, client_key)

        if minute_count >= self.max_per_minute:
            logger.warning(f"Rate limit (minute) exceeded for {client_key}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Demasiadas solicitudes",
                    "message": f"Has excedido el límite de {self.max_per_minute} solicitudes por minuto.",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"}
            )

        if hour_count >= self.max_per_hour:
            logger.warning(f"Rate limit (hour) exceeded for {client_key}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Demasiadas solicitudes",
                    "message": f"Has excedido el límite de {self.max_per_hour} solicitudes por hora.",
                    "retry_after": 3600,
                },
                headers={"Retry-After": "3600"}
            )

        # Incrementar contadores
        if client_key not in self.minute_counts:
            self.minute_counts[client_key] = []
        if client_key not in self.hour_counts:
            self.hour_counts[client_key] = []

        self.minute_counts[client_key].append((now, 1))
        self.hour_counts[client_key].append((now, 1))

        # Agregar headers informativos
        response = await call_next(request)
        response.headers["X-RateLimit-Limit-Minute"] = str(self.max_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            max(0, self.max_per_minute - minute_count - 1)
        )
        response.headers["X-RateLimit-Limit-Hour"] = str(self.max_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            max(0, self.max_per_hour - hour_count - 1)
        )

        return response


class SubscriptionStatusMiddleware(BaseHTTPMiddleware):
    """
    Middleware que verifica el estado de la suscripción del usuario
    y muestra advertencias si está por vencer o tiene problemas de pago
    """

    # Rutas que no requieren suscripción activa
    EXEMPT_ROUTES = [
        "/",
        "/login",
        "/register",
        "/logout",
        "/pricing",
        "/subscription",
        "/subscription/checkout",
        "/subscription/portal",
        "/subscription/success",
        "/webhooks",
        "/static",
    ]

    async def dispatch(self, request: Request, call_next: Callable):
        """Verifica el estado de la suscripción"""

        # Verificar si la ruta está exenta
        path = request.url.path
        if any(path.startswith(route) for route in self.EXEMPT_ROUTES):
            return await call_next(request)

        # Obtener user_id de la sesión
        user_id = request.session.get("user_id")
        if not user_id:
            return await call_next(request)

        # Obtener estado de suscripción
        try:
            subscription = get_or_create_subscription(user_id)
        except Exception as e:
            logger.error(f"Error getting subscription for user {user_id}: {e}")
            return await call_next(request)

        # Plan gratuito (explorer) siempre tiene acceso
        if subscription["plan"] == "explorer":
            return await call_next(request)

        # Verificar si la suscripción tiene problemas
        if subscription["status"] == "past_due":
            # Permitir acceso pero mostrar advertencia
            request.session["subscription_warning"] = (
                "Tu suscripción tiene un pago pendiente. "
                "Actualiza tu método de pago para evitar la interrupción del servicio."
            )
        elif subscription["status"] == "canceled":
            # Degradar a plan gratuito
            logger.info(f"User {user_id} subscription canceled, downgrading to free")
            # Nota: La actualización real debe hacerse en el webhook handler
            request.session["subscription_warning"] = (
                "Tu suscripción ha sido cancelada. "
                "Ahora tienes acceso limitado con el plan gratuito."
            )

        return await call_next(request)
