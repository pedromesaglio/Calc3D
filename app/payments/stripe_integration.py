"""
Integración con Stripe para suscripciones y pagos
"""
import os
import logging
from typing import Literal
import stripe
from datetime import datetime

from ..subscriptions import PLANS, update_subscription, record_payment
from ..database_utils import atomic_transaction
from ..config import Config

logger = logging.getLogger(__name__)


class StripeService:
    """Servicio de integración con Stripe"""

    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self.price_ids = {
            "pro": os.getenv("STRIPE_PRICE_ID_PRO"),
            "business": os.getenv("STRIPE_PRICE_ID_BUSINESS"),
        }

        if self.api_key:
            stripe.api_key = self.api_key

    def is_configured(self) -> bool:
        """Verifica si Stripe está configurado correctamente"""
        return bool(self.api_key and self.webhook_secret)

    def create_customer(self, user_id: int, email: str, username: str) -> str | None:
        """Crea un cliente en Stripe"""
        if not self.is_configured():
            logger.warning("Stripe not configured")
            return None

        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={
                    "user_id": str(user_id),
                    "username": username,
                }
            )
            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return customer.id
        except stripe.StripeError as e:
            logger.error(f"Error creating Stripe customer: {e}")
            return None

    def create_checkout_session(
        self,
        user_id: int,
        customer_id: str,
        plan: Literal["pro", "business"],
        success_url: str,
        cancel_url: str,
    ) -> str | None:
        """Crea una sesión de checkout para suscripción"""
        if not self.is_configured():
            logger.warning("Stripe not configured")
            return None

        price_id = self.price_ids.get(plan)
        if not price_id:
            logger.error(f"No price ID configured for plan {plan}")
            return None

        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                payment_method_types=["card"],
                line_items=[{
                    "price": price_id,
                    "quantity": 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(user_id),
                    "plan": plan,
                },
                subscription_data={
                    "metadata": {
                        "user_id": str(user_id),
                        "plan": plan,
                    },
                    "trial_period_days": Config.TRIAL_PERIOD_DAYS,
                },
            )
            logger.info(f"Created checkout session {session.id} for user {user_id}")
            return session.url
        except stripe.StripeError as e:
            logger.error(f"Error creating checkout session: {e}")
            return None

    def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str | None:
        """Crea una sesión del portal de facturación"""
        if not self.is_configured():
            logger.warning("Stripe not configured")
            return None

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.StripeError as e:
            logger.error(f"Error creating billing portal session: {e}")
            return None

    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancela una suscripción al final del período actual"""
        if not self.is_configured():
            logger.warning("Stripe not configured")
            return False

        try:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            logger.info(f"Canceled subscription {subscription_id}")
            return True
        except stripe.StripeError as e:
            logger.error(f"Error canceling subscription: {e}")
            return False

    def verify_webhook_signature(self, payload: bytes, signature: str) -> dict | None:
        """Verifica la firma del webhook de Stripe"""
        if not self.webhook_secret:
            logger.warning("Stripe webhook secret not configured")
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return event
        except ValueError:
            logger.error("Invalid webhook payload")
            return None
        except stripe.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            return None

    def handle_webhook_event(self, event: dict, db_path: str | None = None) -> bool:
        """Procesa un evento de webhook de Stripe"""
        event_type = event["type"]
        data = event["data"]["object"]

        try:
            if event_type == "checkout.session.completed":
                return self._handle_checkout_completed(data, db_path)

            elif event_type == "customer.subscription.created":
                return self._handle_subscription_created(data, db_path)

            elif event_type == "customer.subscription.updated":
                return self._handle_subscription_updated(data, db_path)

            elif event_type == "customer.subscription.deleted":
                return self._handle_subscription_deleted(data, db_path)

            elif event_type == "invoice.payment_succeeded":
                return self._handle_invoice_payment_succeeded(data, db_path)

            elif event_type == "invoice.payment_failed":
                return self._handle_invoice_payment_failed(data, db_path)

            else:
                logger.info(f"Unhandled Stripe event type: {event_type}")
                return True

        except Exception as e:
            logger.error(f"Error handling Stripe webhook event: {e}")
            return False

    def _handle_checkout_completed(self, session: dict, db_path: str | None = None) -> bool:
        """
        Maneja la finalización del checkout.

        NOTA: update_subscription ya maneja su propia conexión, no necesitamos
        transacción atómica adicional aquí (es una sola operación UPDATE).
        """
        user_id = int(session["metadata"]["user_id"])
        plan = session["metadata"]["plan"]
        customer_id = session["customer"]
        subscription_id = session["subscription"]

        logger.info(f"Checkout completed for user {user_id}, plan {plan}")

        update_subscription(
            user_id=user_id,
            plan=plan,
            status="trialing",  # Inicia en período de prueba
            payment_provider="stripe",
            provider_customer_id=customer_id,
            provider_subscription_id=subscription_id,
            db_path=db_path
        )

        return True

    def _handle_subscription_created(self, subscription: dict, db_path: str | None = None) -> bool:
        """Maneja la creación de una suscripción"""
        user_id = int(subscription["metadata"]["user_id"])
        plan = subscription["metadata"]["plan"]

        status_map = {
            "active": "active",
            "trialing": "trialing",
            "past_due": "past_due",
            "canceled": "canceled",
            "incomplete": "incomplete",
        }

        status = status_map.get(subscription["status"], "incomplete")

        logger.info(f"Subscription created for user {user_id}, status: {status}")

        update_subscription(
            user_id=user_id,
            plan=plan,
            status=status,
            payment_provider="stripe",
            provider_customer_id=subscription["customer"],
            provider_subscription_id=subscription["id"],
            db_path=db_path
        )

        return True

    def _handle_subscription_updated(self, subscription: dict, db_path: str | None = None) -> bool:
        """Maneja la actualización de una suscripción"""
        user_id = int(subscription["metadata"]["user_id"])
        plan = subscription["metadata"]["plan"]

        status_map = {
            "active": "active",
            "trialing": "trialing",
            "past_due": "past_due",
            "canceled": "canceled",
            "incomplete": "incomplete",
        }

        status = status_map.get(subscription["status"], "incomplete")

        logger.info(f"Subscription updated for user {user_id}, status: {status}")

        update_subscription(
            user_id=user_id,
            plan=plan,
            status=status,
            db_path=db_path
        )

        return True

    def _handle_subscription_deleted(self, subscription: dict, db_path: str | None = None) -> bool:
        """Maneja la eliminación de una suscripción"""
        user_id = int(subscription["metadata"]["user_id"])

        logger.info(f"Subscription deleted for user {user_id}")

        # Cambiar a plan gratuito
        update_subscription(
            user_id=user_id,
            plan="free",
            status="canceled",
            db_path=db_path
        )

        return True

    def _handle_invoice_payment_succeeded(self, invoice: dict, db_path: str | None = None) -> bool:
        """
        Maneja el pago exitoso de una factura.

        IMPORTANTE: Usa transacción atómica para garantizar que el registro
        del pago exitoso y la actualización de estado (si aplica) sean una sola operación.
        """
        customer_id = invoice["customer"]
        subscription_id = invoice.get("subscription")

        if not subscription_id:
            return True

        # Obtener la suscripción para extraer el user_id
        subscription = stripe.Subscription.retrieve(subscription_id)
        user_id = int(subscription["metadata"]["user_id"])

        logger.info(f"Invoice payment succeeded for user {user_id}")

        try:
            # Transacción atómica: registrar pago exitoso
            with atomic_transaction(db_path) as conn:
                now = datetime.now().isoformat()
                conn.execute("""
                    INSERT INTO payments
                    (user_id, amount, currency, status, payment_provider,
                     provider_payment_id, provider_customer_id, description,
                     metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    invoice["amount_paid"] / 100,  # Convertir de centavos
                    invoice["currency"].upper(),
                    "succeeded",
                    "stripe",
                    invoice["payment_intent"],
                    customer_id,
                    f"Pago de suscripción - {invoice['id']}",
                    None,
                    now,
                    now
                ))

            logger.info(f"Payment succeeded recorded atomically for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to record successful payment atomically: {e}")
            return False

    def _handle_invoice_payment_failed(self, invoice: dict, db_path: str | None = None) -> bool:
        """
        Maneja el fallo de pago de una factura.

        IMPORTANTE: Usa transacción atómica para garantizar que el registro
        del pago fallido y la actualización de estado sean una sola operación.
        """
        customer_id = invoice["customer"]
        subscription_id = invoice.get("subscription")

        if not subscription_id:
            return True

        # Obtener la suscripción para extraer el user_id
        subscription = stripe.Subscription.retrieve(subscription_id)
        user_id = int(subscription["metadata"]["user_id"])
        plan = subscription["metadata"]["plan"]

        logger.warning(f"Invoice payment failed for user {user_id}")

        try:
            # Transacción atómica: registrar pago Y actualizar suscripción
            with atomic_transaction(db_path) as conn:
                # 1. Registrar el pago fallido
                now = datetime.now().isoformat()
                conn.execute("""
                    INSERT INTO payments
                    (user_id, amount, currency, status, payment_provider,
                     provider_payment_id, provider_customer_id, description,
                     metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    invoice["amount_due"] / 100,
                    invoice["currency"].upper(),
                    "failed",
                    "stripe",
                    invoice["payment_intent"],
                    customer_id,
                    f"Pago fallido de suscripción - {invoice['id']}",
                    None,
                    now,
                    now
                ))

                # 2. Actualizar estado de suscripción a past_due
                conn.execute("""
                    UPDATE subscriptions
                    SET status = 'past_due',
                        updated_at = ?
                    WHERE user_id = ?
                """, (now, user_id))

            logger.info(f"Payment failure recorded and subscription updated atomically for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to handle payment failure atomically: {e}")
            return False


# Instancia global del servicio
stripe_service = StripeService()
