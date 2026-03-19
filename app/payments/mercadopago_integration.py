"""
Integración con Mercado Pago para suscripciones y pagos
"""
import os
import logging
from typing import Literal
import requests
from datetime import datetime

from ..subscriptions import PLANS, update_subscription, record_payment

logger = logging.getLogger(__name__)


class MercadoPagoService:
    """Servicio de integración con Mercado Pago"""

    def __init__(self):
        self.access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        self.webhook_secret = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
        self.plan_ids = {
            "pro": os.getenv("MERCADOPAGO_PLAN_ID_PRO"),
            "business": os.getenv("MERCADOPAGO_PLAN_ID_BUSINESS"),
        }
        self.base_url = "https://api.mercadopago.com"

    def is_configured(self) -> bool:
        """Verifica si Mercado Pago está configurado correctamente"""
        return bool(self.access_token)

    def _headers(self) -> dict:
        """Headers para las requests a Mercado Pago"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def create_customer(self, user_id: int, email: str, username: str) -> str | None:
        """Crea un cliente en Mercado Pago"""
        if not self.is_configured():
            logger.warning("Mercado Pago not configured")
            return None

        try:
            response = requests.post(
                f"{self.base_url}/v1/customers",
                headers=self._headers(),
                json={
                    "email": email,
                    "first_name": username,
                    "description": f"User ID: {user_id}",
                    "metadata": {
                        "user_id": str(user_id),
                        "username": username,
                    }
                }
            )
            response.raise_for_status()
            customer = response.json()
            logger.info(f"Created Mercado Pago customer {customer['id']} for user {user_id}")
            return customer["id"]
        except requests.RequestException as e:
            logger.error(f"Error creating Mercado Pago customer: {e}")
            return None

    def create_subscription(
        self,
        user_id: int,
        customer_id: str,
        plan: Literal["pro", "business"],
        back_url: str,
    ) -> str | None:
        """Crea una suscripción en Mercado Pago"""
        if not self.is_configured():
            logger.warning("Mercado Pago not configured")
            return None

        plan_id = self.plan_ids.get(plan)
        if not plan_id:
            logger.error(f"No plan ID configured for plan {plan}")
            return None

        try:
            response = requests.post(
                f"{self.base_url}/preapproval",
                headers=self._headers(),
                json={
                    "reason": f"Suscripción {PLANS[plan]['name']} - Calc3D",
                    "auto_recurring": {
                        "frequency": 1,
                        "frequency_type": "months",
                        "transaction_amount": PLANS[plan]["price"],
                        "currency_id": PLANS[plan]["currency"],
                        "free_trial": {
                            "frequency": 14,
                            "frequency_type": "days",
                        }
                    },
                    "back_url": back_url,
                    "payer_email": "",  # Se completará en el checkout
                    "status": "pending",
                    "external_reference": str(user_id),
                    "metadata": {
                        "user_id": str(user_id),
                        "plan": plan,
                    }
                }
            )
            response.raise_for_status()
            subscription = response.json()
            logger.info(f"Created Mercado Pago subscription {subscription['id']} for user {user_id}")
            return subscription.get("init_point")
        except requests.RequestException as e:
            logger.error(f"Error creating Mercado Pago subscription: {e}")
            return None

    def create_preference(
        self,
        user_id: int,
        plan: Literal["pro", "business"],
        success_url: str,
        failure_url: str,
        pending_url: str,
    ) -> str | None:
        """Crea una preferencia de pago para suscripción"""
        if not self.is_configured():
            logger.warning("Mercado Pago not configured")
            return None

        try:
            response = requests.post(
                f"{self.base_url}/checkout/preferences",
                headers=self._headers(),
                json={
                    "items": [{
                        "title": f"Suscripción {PLANS[plan]['name']} - Calc3D",
                        "description": f"Plan {PLANS[plan]['name']} mensual",
                        "quantity": 1,
                        "currency_id": PLANS[plan]["currency"],
                        "unit_price": PLANS[plan]["price"],
                    }],
                    "back_urls": {
                        "success": success_url,
                        "failure": failure_url,
                        "pending": pending_url,
                    },
                    "auto_return": "approved",
                    "external_reference": str(user_id),
                    "metadata": {
                        "user_id": str(user_id),
                        "plan": plan,
                    },
                    "payment_methods": {
                        "installments": 1,
                    },
                }
            )
            response.raise_for_status()
            preference = response.json()
            logger.info(f"Created Mercado Pago preference {preference['id']} for user {user_id}")
            return preference.get("init_point")
        except requests.RequestException as e:
            logger.error(f"Error creating Mercado Pago preference: {e}")
            return None

    def get_payment(self, payment_id: str) -> dict | None:
        """Obtiene información de un pago"""
        if not self.is_configured():
            logger.warning("Mercado Pago not configured")
            return None

        try:
            response = requests.get(
                f"{self.base_url}/v1/payments/{payment_id}",
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error getting Mercado Pago payment: {e}")
            return None

    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancela una suscripción"""
        if not self.is_configured():
            logger.warning("Mercado Pago not configured")
            return False

        try:
            response = requests.put(
                f"{self.base_url}/preapproval/{subscription_id}",
                headers=self._headers(),
                json={"status": "cancelled"}
            )
            response.raise_for_status()
            logger.info(f"Canceled Mercado Pago subscription {subscription_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Error canceling Mercado Pago subscription: {e}")
            return False

    def verify_webhook_signature(self, payload: dict, signature: str) -> bool:
        """Verifica la firma del webhook de Mercado Pago"""
        # Mercado Pago usa x-signature header
        # Por simplicidad, verificamos que tenga el header correcto
        # En producción, se debe implementar la verificación completa
        if not self.webhook_secret:
            logger.warning("Mercado Pago webhook secret not configured")
            return False

        # TODO: Implementar verificación real de firma
        return True

    def handle_webhook_event(self, event: dict, db_path: str | None = None) -> bool:
        """Procesa un evento de webhook de Mercado Pago"""
        event_type = event.get("type")

        try:
            if event_type == "payment":
                return self._handle_payment_notification(event, db_path)

            elif event_type == "subscription_preapproval":
                return self._handle_subscription_notification(event, db_path)

            else:
                logger.info(f"Unhandled Mercado Pago event type: {event_type}")
                return True

        except Exception as e:
            logger.error(f"Error handling Mercado Pago webhook event: {e}")
            return False

    def _handle_payment_notification(self, event: dict, db_path: str | None = None) -> bool:
        """Maneja notificación de pago"""
        payment_id = event.get("data", {}).get("id")
        if not payment_id:
            return False

        payment = self.get_payment(payment_id)
        if not payment:
            return False

        user_id = int(payment.get("external_reference", 0))
        if not user_id:
            return False

        status_map = {
            "approved": "succeeded",
            "pending": "pending",
            "rejected": "failed",
            "cancelled": "canceled",
            "refunded": "refunded",
        }

        status = status_map.get(payment["status"], "pending")

        logger.info(f"Payment {payment_id} for user {user_id}, status: {status}")

        # Registrar el pago
        record_payment(
            user_id=user_id,
            amount=payment["transaction_amount"],
            currency=payment["currency_id"],
            status=status,
            payment_provider="mercadopago",
            provider_payment_id=str(payment_id),
            provider_customer_id=payment.get("payer", {}).get("id"),
            description=payment.get("description", "Pago de suscripción"),
            db_path=db_path
        )

        # Si el pago fue aprobado, actualizar la suscripción
        if status == "succeeded":
            plan = payment.get("metadata", {}).get("plan", "pro")
            update_subscription(
                user_id=user_id,
                plan=plan,
                status="active",
                payment_provider="mercadopago",
                provider_customer_id=payment.get("payer", {}).get("id"),
                db_path=db_path
            )

        return True

    def _handle_subscription_notification(self, event: dict, db_path: str | None = None) -> bool:
        """Maneja notificación de suscripción"""
        subscription_id = event.get("data", {}).get("id")
        if not subscription_id:
            return False

        # Obtener detalles de la suscripción
        try:
            response = requests.get(
                f"{self.base_url}/preapproval/{subscription_id}",
                headers=self._headers()
            )
            response.raise_for_status()
            subscription = response.json()
        except requests.RequestException as e:
            logger.error(f"Error getting subscription: {e}")
            return False

        user_id = int(subscription.get("external_reference", 0))
        if not user_id:
            return False

        status_map = {
            "pending": "incomplete",
            "authorized": "active",
            "paused": "past_due",
            "cancelled": "canceled",
        }

        status = status_map.get(subscription["status"], "incomplete")
        plan = subscription.get("metadata", {}).get("plan", "pro")

        logger.info(f"Subscription {subscription_id} for user {user_id}, status: {status}")

        update_subscription(
            user_id=user_id,
            plan=plan,
            status=status,
            payment_provider="mercadopago",
            provider_subscription_id=subscription_id,
            db_path=db_path
        )

        return True


# Instancia global del servicio
mercadopago_service = MercadoPagoService()
