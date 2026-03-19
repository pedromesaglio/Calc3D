"""
Tests para el sistema de suscripciones
"""
import pytest
from datetime import datetime, timedelta
from app.subscriptions import (
    PLANS,
    get_or_create_subscription,
    get_usage_limits,
    check_limit,
    increment_usage,
    update_subscription,
    has_feature,
    get_user_plan_info,
)


@pytest.fixture
def test_user_id():
    """ID de usuario de prueba"""
    return 1


def test_create_free_subscription(test_db, test_user_id):
    """Test: Crear suscripción gratuita por defecto"""
    subscription = get_or_create_subscription(test_user_id, test_db)

    assert subscription is not None
    assert subscription["user_id"] == test_user_id
    assert subscription["plan"] == "free"
    assert subscription["status"] == "active"


def test_usage_limits_creation(test_db, test_user_id):
    """Test: Crear límites de uso automáticamente"""
    # Crear suscripción (crea límites también)
    get_or_create_subscription(test_user_id, test_db)

    usage = get_usage_limits(test_user_id, test_db)

    assert usage is not None
    assert usage["user_id"] == test_user_id
    assert usage["calculations_used"] == 0
    assert usage["quotes_used"] == 0
    assert usage["clients_used"] == 0
    assert usage["catalog_items_used"] == 0


def test_check_limit_free_plan(test_db, test_user_id):
    """Test: Verificar límites en plan gratuito"""
    get_or_create_subscription(test_user_id, test_db)

    # Dentro del límite
    can_use, error = check_limit(test_user_id, "calculations", test_db)
    assert can_use is True
    assert error == ""

    # Alcanzar el límite
    for _ in range(20):
        increment_usage(test_user_id, "calculations", 1, test_db)

    can_use, error = check_limit(test_user_id, "calculations", test_db)
    assert can_use is False
    assert "límite" in error.lower()


def test_check_limit_pro_plan(test_db, test_user_id):
    """Test: Plan Pro tiene límites ilimitados en cálculos"""
    get_or_create_subscription(test_user_id, test_db)
    update_subscription(test_user_id, "pro", db_path=test_db)

    # Incrementar mucho más que el límite gratuito
    for _ in range(100):
        increment_usage(test_user_id, "calculations", 1, test_db)

    can_use, error = check_limit(test_user_id, "calculations", test_db)
    assert can_use is True  # Ilimitado


def test_increment_usage(test_db, test_user_id):
    """Test: Incrementar uso de recursos"""
    get_or_create_subscription(test_user_id, test_db)

    increment_usage(test_user_id, "calculations", 5, test_db)
    usage = get_usage_limits(test_user_id, test_db)

    assert usage["calculations_used"] == 5


def test_update_subscription_to_pro(test_db, test_user_id):
    """Test: Actualizar de free a pro"""
    get_or_create_subscription(test_user_id, test_db)

    update_subscription(
        user_id=test_user_id,
        plan="pro",
        status="active",
        payment_provider="stripe",
        provider_customer_id="cus_test123",
        db_path=test_db
    )

    subscription = get_or_create_subscription(test_user_id, test_db)

    assert subscription["plan"] == "pro"
    assert subscription["status"] == "active"
    assert subscription["payment_provider"] == "stripe"
    assert subscription["stripe_customer_id"] == "cus_test123"


def test_has_feature_free_plan(test_db, test_user_id):
    """Test: Plan gratuito no tiene features premium"""
    get_or_create_subscription(test_user_id, test_db)

    assert has_feature(test_user_id, "pdf_export", test_db) is False
    assert has_feature(test_user_id, "email_quotes", test_db) is False
    assert has_feature(test_user_id, "analytics", test_db) is False


def test_has_feature_pro_plan(test_db, test_user_id):
    """Test: Plan Pro tiene algunas features premium"""
    get_or_create_subscription(test_user_id, test_db)
    update_subscription(test_user_id, "pro", status="active", db_path=test_db)

    assert has_feature(test_user_id, "pdf_export", test_db) is True
    assert has_feature(test_user_id, "email_quotes", test_db) is True
    assert has_feature(test_user_id, "analytics", test_db) is True
    assert has_feature(test_user_id, "api_access", test_db) is False


def test_has_feature_business_plan(test_db, test_user_id):
    """Test: Plan Business tiene todas las features"""
    get_or_create_subscription(test_user_id, test_db)
    update_subscription(test_user_id, "business", status="active", db_path=test_db)

    assert has_feature(test_user_id, "pdf_export", test_db) is True
    assert has_feature(test_user_id, "api_access", test_db) is True
    assert has_feature(test_user_id, "custom_branding", test_db) is True


def test_get_user_plan_info(test_db, test_user_id):
    """Test: Obtener información completa del plan"""
    get_or_create_subscription(test_user_id, test_db)
    increment_usage(test_user_id, "calculations", 10, test_db)

    plan_info = get_user_plan_info(test_user_id, test_db)

    assert plan_info is not None
    assert "subscription" in plan_info
    assert "plan" in plan_info
    assert "usage" in plan_info
    assert "usage_percentages" in plan_info
    assert plan_info["is_active"] is True
    assert plan_info["can_upgrade"] is True

    # Verificar porcentaje de uso
    # Free plan: 20 cálculos, usado 10 = 50%
    assert plan_info["usage_percentages"]["calculations"] == 50.0


def test_usage_limits_reset(test_db, test_user_id):
    """Test: Reset de límites de uso (simulado)"""
    from app.db import get_db

    get_or_create_subscription(test_user_id, test_db)
    increment_usage(test_user_id, "calculations", 15, test_db)

    # Simular que pasó el período de reset
    past_date = (datetime.now() - timedelta(days=31)).isoformat()

    with get_db(test_db) as conn:
        conn.execute(
            "UPDATE usage_limits SET reset_at = ? WHERE user_id = ?",
            (past_date, test_user_id)
        )

    # Al consultar límites, debe resetear automáticamente
    usage = get_usage_limits(test_user_id, test_db)

    assert usage["calculations_used"] == 0  # Se reseteó
    assert usage["quotes_used"] == 0


def test_plans_configuration():
    """Test: Verificar configuración de planes"""
    assert "free" in PLANS
    assert "pro" in PLANS
    assert "business" in PLANS

    # Verificar estructura del plan gratuito
    free_plan = PLANS["free"]
    assert free_plan["price"] == 0
    assert free_plan["calculations_limit"] == 20
    assert free_plan["features"]["pdf_export"] is False

    # Verificar plan pro
    pro_plan = PLANS["pro"]
    assert pro_plan["price"] > 0
    assert pro_plan["calculations_limit"] == -1  # Ilimitado
    assert pro_plan["features"]["pdf_export"] is True

    # Verificar plan business
    business_plan = PLANS["business"]
    assert business_plan["price"] > pro_plan["price"]
    assert business_plan["calculations_limit"] == -1
    assert business_plan["features"]["api_access"] is True
