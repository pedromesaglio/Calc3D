"""
Sistema de suscripciones y límites de uso para Calc3D
"""
from datetime import datetime, timedelta
from typing import Literal
from .db import get_db
from .config import Config


# Definición de planes y sus límites
PLANS = {
    "free": {
        "name": "Gratuito",
        "price": 0,
        "currency": "USD",
        "calculations_limit": 20,
        "quotes_limit": 5,
        "clients_limit": 5,
        "catalog_items_limit": 10,
        "features": {
            "pdf_export": False,
            "email_quotes": False,
            "analytics": False,
            "priority_support": False,
            "custom_branding": False,
            "api_access": False,
        }
    },
    "pro": {
        "name": "Profesional",
        "price": 9.99,
        "currency": "USD",
        "calculations_limit": -1,  # -1 significa ilimitado
        "quotes_limit": 100,
        "clients_limit": 50,
        "catalog_items_limit": 100,
        "features": {
            "pdf_export": True,
            "email_quotes": True,
            "analytics": True,
            "priority_support": False,
            "custom_branding": False,
            "api_access": False,
        }
    },
    "business": {
        "name": "Empresa",
        "price": 29.99,
        "currency": "USD",
        "calculations_limit": -1,
        "quotes_limit": -1,
        "clients_limit": -1,
        "catalog_items_limit": -1,
        "features": {
            "pdf_export": True,
            "email_quotes": True,
            "analytics": True,
            "priority_support": True,
            "custom_branding": True,
            "api_access": True,
        }
    }
}


PlanType = Literal["free", "pro", "business"]
SubscriptionStatus = Literal["active", "canceled", "past_due", "trialing", "incomplete"]


def get_or_create_subscription(user_id: int, db_path: str | None = None) -> dict:
    """Obtiene o crea la suscripción de un usuario"""
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row:
            return dict(row)

        # Crear suscripción gratuita por defecto
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO subscriptions
            (user_id, plan, status, started_at, created_at, updated_at)
            VALUES (?, 'free', 'active', ?, ?, ?)
        """, (user_id, now, now, now))

        # Crear límites de uso
        next_reset = (datetime.now() + timedelta(days=Config.USAGE_RESET_PERIOD_DAYS)).isoformat()
        conn.execute("""
            INSERT INTO usage_limits
            (user_id, reset_at, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, next_reset, now, now))

        # Commit para que los datos estén disponibles
        conn.commit()

        # Consultar directamente lo que acabamos de crear (sin recursión)
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchone()

        return dict(row) if row else {}


def get_usage_limits(user_id: int, db_path: str | None = None) -> dict:
    """Obtiene los límites de uso actuales del usuario"""
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM usage_limits WHERE user_id = ?", (user_id,)
        ).fetchone()

        if not row:
            # Crear límites si no existen
            now = datetime.now().isoformat()
            next_reset = (datetime.now() + timedelta(days=Config.USAGE_RESET_PERIOD_DAYS)).isoformat()
            conn.execute("""
                INSERT INTO usage_limits
                (user_id, reset_at, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, next_reset, now, now))
            conn.commit()

            # Consultar directamente lo que acabamos de crear (sin recursión)
            row = conn.execute(
                "SELECT * FROM usage_limits WHERE user_id = ?", (user_id,)
            ).fetchone()

        if not row:
            # Esto no debería pasar nunca, pero por seguridad
            return {
                "user_id": user_id,
                "calculations_used": 0,
                "quotes_used": 0,
                "clients_used": 0,
                "catalog_items_used": 0,
            }

        limits = dict(row)

        # Verificar si necesita reset
        reset_at = datetime.fromisoformat(limits["reset_at"])
        if datetime.now() >= reset_at:
            next_reset = (datetime.now() + timedelta(days=Config.USAGE_RESET_PERIOD_DAYS)).isoformat()
            conn.execute("""
                UPDATE usage_limits
                SET calculations_used = 0,
                    quotes_used = 0,
                    clients_used = 0,
                    catalog_items_used = 0,
                    reset_at = ?,
                    updated_at = ?
                WHERE user_id = ?
            """, (next_reset, datetime.now().isoformat(), user_id))
            conn.commit()

            # Consultar directamente los datos actualizados (sin recursión)
            row = conn.execute(
                "SELECT * FROM usage_limits WHERE user_id = ?", (user_id,)
            ).fetchone()
            limits = dict(row) if row else limits

        return limits


def check_limit(
    user_id: int,
    resource_type: Literal["calculations", "quotes", "clients", "catalog_items"],
    db_path: str | None = None
) -> tuple[bool, str]:
    """
    Verifica si el usuario puede usar un recurso
    Retorna (puede_usar, mensaje_error)
    """
    subscription = get_or_create_subscription(user_id, db_path)
    usage = get_usage_limits(user_id, db_path)
    plan = PLANS.get(subscription["plan"], PLANS["free"])

    limit_key = f"{resource_type}_limit"
    used_key = f"{resource_type}_used"

    limit = plan.get(limit_key, 0)
    used = usage.get(used_key, 0)

    # -1 significa ilimitado
    if limit == -1:
        return True, ""

    if used >= limit:
        return False, f"Has alcanzado el límite de {limit} {resource_type} para tu plan {plan['name']}. Actualiza tu plan para continuar."

    return True, ""


def increment_usage(
    user_id: int,
    resource_type: Literal["calculations", "quotes", "clients", "catalog_items"],
    amount: int = 1,
    db_path: str | None = None
) -> None:
    """Incrementa el contador de uso de un recurso"""
    used_key = f"{resource_type}_used"

    with get_db(db_path) as conn:
        conn.execute(f"""
            UPDATE usage_limits
            SET {used_key} = {used_key} + ?,
                updated_at = ?
            WHERE user_id = ?
        """, (amount, datetime.now().isoformat(), user_id))


def get_user_plan_info(user_id: int, db_path: str | None = None) -> dict:
    """Obtiene información completa del plan del usuario"""
    subscription = get_or_create_subscription(user_id, db_path)
    usage = get_usage_limits(user_id, db_path)
    plan = PLANS.get(subscription["plan"], PLANS["free"])

    # Calcular porcentajes de uso
    usage_percentages = {}
    for resource in ["calculations", "quotes", "clients", "catalog_items"]:
        limit = plan.get(f"{resource}_limit", 0)
        used = usage.get(f"{resource}_used", 0)

        if limit == -1:
            usage_percentages[resource] = 0  # Ilimitado
        elif limit == 0:
            usage_percentages[resource] = 100
        else:
            usage_percentages[resource] = (used / limit) * 100

    return {
        "subscription": subscription,
        "plan": plan,
        "usage": usage,
        "usage_percentages": usage_percentages,
        "is_active": subscription["status"] == "active",
        "can_upgrade": subscription["plan"] != "business",
    }


def update_subscription(
    user_id: int,
    plan: PlanType,
    status: SubscriptionStatus | None = None,
    payment_provider: str | None = None,
    provider_customer_id: str | None = None,
    provider_subscription_id: str | None = None,
    db_path: str | None = None
) -> None:
    """Actualiza la suscripción de un usuario"""
    now = datetime.now().isoformat()

    updates = {"plan": plan, "updated_at": now}

    if status:
        updates["status"] = status
    if payment_provider:
        updates["payment_provider"] = payment_provider

    if provider_customer_id:
        if payment_provider == "stripe":
            updates["stripe_customer_id"] = provider_customer_id
        elif payment_provider == "mercadopago":
            updates["mercadopago_customer_id"] = provider_customer_id

    if provider_subscription_id:
        if payment_provider == "stripe":
            updates["stripe_subscription_id"] = provider_subscription_id
        elif payment_provider == "mercadopago":
            updates["mercadopago_subscription_id"] = provider_subscription_id

    # Si es la primera vez que activa un plan de pago
    subscription = get_or_create_subscription(user_id, db_path)
    if subscription["plan"] == "free" and plan != "free":
        updates["started_at"] = now
        updates["current_period_start"] = now
        updates["current_period_end"] = (
            datetime.now() + timedelta(days=Config.BILLING_CYCLE_DAYS)
        ).isoformat()

    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [user_id]

    with get_db(db_path) as conn:
        conn.execute(
            f"UPDATE subscriptions SET {set_clause} WHERE user_id = ?",
            values
        )


def cancel_subscription(user_id: int, db_path: str | None = None) -> None:
    """Cancela la suscripción de un usuario (al final del período actual)"""
    now = datetime.now().isoformat()

    with get_db(db_path) as conn:
        conn.execute("""
            UPDATE subscriptions
            SET status = 'canceled',
                canceled_at = ?,
                updated_at = ?
            WHERE user_id = ?
        """, (now, now, user_id))


def has_feature(user_id: int, feature: str, db_path: str | None = None) -> bool:
    """Verifica si el usuario tiene acceso a una característica específica"""
    subscription = get_or_create_subscription(user_id, db_path)
    plan = PLANS.get(subscription["plan"], PLANS["free"])

    if subscription["status"] != "active":
        return False

    return plan.get("features", {}).get(feature, False)


def record_payment(
    user_id: int,
    amount: float,
    currency: str,
    status: str,
    payment_provider: str,
    provider_payment_id: str | None = None,
    provider_customer_id: str | None = None,
    description: str | None = None,
    metadata: str | None = None,
    db_path: str | None = None
) -> int:
    """Registra un pago en la base de datos"""
    now = datetime.now().isoformat()

    with get_db(db_path) as conn:
        cursor = conn.execute("""
            INSERT INTO payments
            (user_id, amount, currency, status, payment_provider,
             provider_payment_id, provider_customer_id, description,
             metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, amount, currency, status, payment_provider,
            provider_payment_id, provider_customer_id, description,
            metadata, now, now
        ))
        return cursor.lastrowid


def get_subscription_status_badge(status: str) -> dict:
    """Retorna información de badge para el estado de suscripción"""
    badges = {
        "active": {"text": "Activa", "color": "green"},
        "trialing": {"text": "Prueba", "color": "blue"},
        "past_due": {"text": "Pago Vencido", "color": "yellow"},
        "canceled": {"text": "Cancelada", "color": "red"},
        "incomplete": {"text": "Incompleta", "color": "gray"},
    }
    return badges.get(status, {"text": status, "color": "gray"})
