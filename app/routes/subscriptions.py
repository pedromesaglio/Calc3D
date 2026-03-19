"""
Rutas para gestión de suscripciones y pagos
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.status import HTTP_303_SEE_OTHER
from pydantic import ValidationError

from ..subscriptions import (
    PLANS,
    get_user_plan_info,
    update_subscription,
    cancel_subscription,
    has_feature,
)
from ..payments.stripe_integration import stripe_service
from ..payments.mercadopago_integration import mercadopago_service
from ..db import get_db
from ..csrf import validate_csrf
from .auth import get_current_user
from ..models import CheckoutRequest, PlanType, PaymentProvider
from ..webhook_retry import schedule_webhook_retry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pricing")
async def pricing(request: Request):
    """Página de planes y precios"""
    templates = request.app.state.templates
    user_id = request.session.get("user_id")

    context = {
        "request": request,
        "plans": PLANS,
        "user": None,
    }

    if user_id:
        plan_info = get_user_plan_info(user_id)
        context["user"] = {
            "id": user_id,
            "plan_info": plan_info,
        }

    return templates.TemplateResponse("pricing.html", context)


@router.get("/subscription")
async def subscription_dashboard(request: Request, current_user = Depends(get_current_user)):
    """Panel de gestión de suscripción"""
    templates = request.app.state.templates
    user_id = current_user["id"]

    plan_info = get_user_plan_info(user_id)

    # Obtener historial de pagos
    with get_db() as conn:
        payments = conn.execute(
            """SELECT * FROM payments
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT 20""",
            (user_id,)
        ).fetchall()

    context = {
        "request": request,
        "plans": PLANS,
        "plan_info": plan_info,
        "payments": [dict(p) for p in payments],
        "stripe_configured": stripe_service.is_configured(),
        "mercadopago_configured": mercadopago_service.is_configured(),
    }

    return templates.TemplateResponse("subscription.html", context)


@router.get("/subscription/checkout/{plan}")
async def checkout_page(
    plan: str,
    request: Request,
    current_user = Depends(get_current_user)
):
    """Página de checkout para seleccionar método de pago"""
    templates = request.app.state.templates
    user_id = current_user["id"]

    if plan not in ["pro", "business"]:
        raise HTTPException(status_code=400, detail="Plan inválido")

    plan_info = get_user_plan_info(user_id)
    selected_plan = PLANS.get(plan)

    context = {
        "request": request,
        "plan": plan,
        "plan_details": selected_plan,
        "current_plan": plan_info["subscription"]["plan"],
        "stripe_configured": stripe_service.is_configured(),
        "mercadopago_configured": mercadopago_service.is_configured(),
    }

    return templates.TemplateResponse("checkout.html", context)


@router.post("/subscription/checkout")
async def create_checkout_session(
    request: Request,
    plan: str = Form(...),
    provider: str = Form(...),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user)
):
    """
    Crea una sesión de checkout para suscripción.

    Usa validación Pydantic para garantizar datos correctos.
    """
    user_id = current_user["id"]

    # Validar CSRF
    if csrf_token:
        try:
            validate_csrf(request, csrf_token)
        except HTTPException:
            raise HTTPException(status_code=403, detail="CSRF token inválido")

    # Validar datos con Pydantic
    try:
        checkout_data = CheckoutRequest(plan=plan, provider=provider)
    except ValidationError as e:
        errors = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        raise HTTPException(status_code=400, detail=f"Datos inválidos: {errors}")

    # Obtener información del usuario
    with get_db() as conn:
        user = conn.execute(
            "SELECT username FROM users WHERE id = ?", (user_id,)
        ).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    username = user["username"]
    email = f"{username}@calc3d.local"  # Idealmente deberías tener email en BD

    # Obtener o crear customer ID
    subscription = get_user_plan_info(user_id)["subscription"]

    success_url = str(request.url_for("subscription_success"))
    cancel_url = str(request.url_for("subscription_dashboard"))

    # Usar datos validados
    plan_value = checkout_data.plan
    provider_value = checkout_data.provider

    if provider_value == "stripe":
        customer_id = subscription.get("stripe_customer_id")

        if not customer_id:
            customer_id = stripe_service.create_customer(user_id, email, username)
            if customer_id:
                update_subscription(
                    user_id=user_id,
                    plan=subscription["plan"],
                    payment_provider="stripe",
                    provider_customer_id=customer_id,
                )

        if not customer_id:
            raise HTTPException(
                status_code=500,
                detail="No se pudo crear el cliente en Stripe"
            )

        checkout_url = stripe_service.create_checkout_session(
            user_id=user_id,
            customer_id=customer_id,
            plan=plan_value,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        if not checkout_url:
            raise HTTPException(
                status_code=500,
                detail="No se pudo crear la sesión de checkout"
            )

        return RedirectResponse(url=checkout_url, status_code=HTTP_303_SEE_OTHER)

    elif provider_value == "mercadopago":
        preference_url = mercadopago_service.create_preference(
            user_id=user_id,
            plan=plan_value,
            success_url=success_url,
            failure_url=cancel_url,
            pending_url=cancel_url,
        )

        if not preference_url:
            raise HTTPException(
                status_code=500,
                detail="No se pudo crear la preferencia de pago"
            )

        return RedirectResponse(url=preference_url, status_code=HTTP_303_SEE_OTHER)


@router.get("/subscription/success")
async def subscription_success(request: Request):
    """Página de éxito tras checkout"""
    templates = request.app.state.templates
    return templates.TemplateResponse("subscription_success.html", {"request": request})


@router.post("/subscription/portal")
async def create_portal_session(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Crea una sesión del portal de facturación de Stripe"""
    user_id = current_user["id"]
    form = await request.form()

    # Validar CSRF
    csrf_token = form.get("csrf_token")
    if csrf_token:
        try:
            validate_csrf(request, csrf_token)
        except HTTPException:
            raise HTTPException(status_code=403, detail="CSRF token inválido")

    subscription = get_user_plan_info(user_id)["subscription"]
    customer_id = subscription.get("stripe_customer_id")

    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="No tienes una suscripción activa en Stripe"
        )

    return_url = str(request.url_for("subscription_dashboard"))
    portal_url = stripe_service.create_billing_portal_session(
        customer_id=customer_id,
        return_url=return_url,
    )

    if not portal_url:
        raise HTTPException(
            status_code=500,
            detail="No se pudo crear la sesión del portal"
        )

    return RedirectResponse(url=portal_url, status_code=HTTP_303_SEE_OTHER)


@router.post("/subscription/cancel")
async def cancel_user_subscription(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Cancela la suscripción del usuario"""
    user_id = current_user["id"]
    form = await request.form()

    # Validar CSRF
    csrf_token = form.get("csrf_token")
    if csrf_token:
        try:
            validate_csrf(request, csrf_token)
        except HTTPException:
            raise HTTPException(status_code=403, detail="CSRF token inválido")

    subscription = get_user_plan_info(user_id)["subscription"]
    provider = subscription.get("payment_provider")

    if provider == "stripe":
        subscription_id = subscription.get("stripe_subscription_id")
        if subscription_id:
            success = stripe_service.cancel_subscription(subscription_id)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="No se pudo cancelar la suscripción en Stripe"
                )

    elif provider == "mercadopago":
        subscription_id = subscription.get("mercadopago_subscription_id")
        if subscription_id:
            success = mercadopago_service.cancel_subscription(subscription_id)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="No se pudo cancelar la suscripción en Mercado Pago"
                )

    # Marcar como cancelada en nuestra BD
    cancel_subscription(user_id)

    return RedirectResponse(
        url=request.url_for("subscription_dashboard"),
        status_code=HTTP_303_SEE_OTHER
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Endpoint para webhooks de Stripe"""
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    event = stripe_service.verify_webhook_signature(payload, signature)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Registrar evento
    with get_db() as conn:
        conn.execute(
            """INSERT INTO webhook_events
               (provider, event_type, event_id, payload, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "stripe",
                event["type"],
                event["id"],
                str(event),
                __import__("datetime").datetime.now().isoformat(),
            )
        )

    # Procesar evento
    success = stripe_service.handle_webhook_event(event)

    if success:
        # Marcar como procesado
        with get_db() as conn:
            conn.execute(
                """UPDATE webhook_events
                   SET processed = 1, processed_at = ?
                   WHERE event_id = ?""",
                (__import__("datetime").datetime.now().isoformat(), event["id"])
            )
    else:
        # Programar reintento automático
        logger.warning(f"Procesamiento de webhook {event['id']} falló, programando reintento")
        schedule_webhook_retry(event_id=event["id"], provider="stripe", attempt=1)

    return JSONResponse({"received": True})


@router.post("/webhooks/mercadopago")
async def mercadopago_webhook(request: Request):
    """Endpoint para webhooks de Mercado Pago"""
    event = await request.json()
    signature = request.headers.get("x-signature", "")

    # Verificar firma
    if not mercadopago_service.verify_webhook_signature(event, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_id = event.get("id", str(__import__("uuid").uuid4()))

    # Registrar evento
    with get_db() as conn:
        conn.execute(
            """INSERT INTO webhook_events
               (provider, event_type, event_id, payload, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "mercadopago",
                event.get("type", "unknown"),
                str(event_id),
                str(event),
                __import__("datetime").datetime.now().isoformat(),
            )
        )

    # Procesar evento
    success = mercadopago_service.handle_webhook_event(event)

    if success:
        # Marcar como procesado
        with get_db() as conn:
            conn.execute(
                """UPDATE webhook_events
                   SET processed = 1, processed_at = ?
                   WHERE event_id = ?""",
                (__import__("datetime").datetime.now().isoformat(), str(event_id))
            )
    else:
        # Programar reintento automático
        logger.warning(f"Procesamiento de webhook {event_id} falló, programando reintento")
        schedule_webhook_retry(event_id=str(event_id), provider="mercadopago", attempt=1)

    return JSONResponse({"received": True})
