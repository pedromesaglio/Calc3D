"""
Sistema de reintentos para webhooks de pago

Implementa reintentos exponenciales con backoff para eventos de webhook
que fallan en el procesamiento.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from .db import get_db
from .config import Config

logger = logging.getLogger(__name__)


# Configuración de reintentos
MAX_RETRY_ATTEMPTS = 5
INITIAL_RETRY_DELAY_SECONDS = 60  # 1 minuto
BACKOFF_MULTIPLIER = 2  # Duplica el tiempo de espera en cada reintento


def schedule_webhook_retry(event_id: str, provider: str, attempt: int = 1, db_path: str | None = None) -> None:
    """
    Programa un reintento para un webhook que falló.

    Args:
        event_id: ID del evento de webhook
        provider: Proveedor de pago (stripe, mercadopago)
        attempt: Número de intento actual (1-indexed)
        db_path: Ruta opcional a la base de datos (para tests)
    """
    if attempt > MAX_RETRY_ATTEMPTS:
        logger.error(f"Webhook {event_id} alcanzó el máximo de {MAX_RETRY_ATTEMPTS} reintentos")
        _mark_webhook_failed(event_id, db_path)
        return

    # Calcular tiempo de espera con backoff exponencial
    delay_seconds = INITIAL_RETRY_DELAY_SECONDS * (BACKOFF_MULTIPLIER ** (attempt - 1))
    retry_at = (datetime.now() + timedelta(seconds=delay_seconds)).isoformat()

    logger.info(
        f"Programando reintento {attempt}/{MAX_RETRY_ATTEMPTS} para webhook {event_id} "
        f"en {delay_seconds}s (retry_at: {retry_at})"
    )

    with get_db(db_path) as conn:
        conn.execute(
            """UPDATE webhook_events
               SET retry_count = ?,
                   retry_at = ?,
                   updated_at = ?
               WHERE event_id = ?""",
            (attempt, retry_at, datetime.now().isoformat(), event_id)
        )


def retry_pending_webhooks(db_path: str | None = None) -> int:
    """
    Procesa webhooks pendientes de reintento.

    Esta función debe ser llamada periódicamente (ej: cada minuto vía cron/scheduler).

    Args:
        db_path: Ruta opcional a la base de datos (para tests)

    Returns:
        Número de webhooks procesados exitosamente
    """
    now = datetime.now().isoformat()
    successful_retries = 0

    with get_db(db_path) as conn:
        # Obtener webhooks listos para reintentar
        pending_webhooks = conn.execute(
            """SELECT event_id, provider, event_type, payload, retry_count
               FROM webhook_events
               WHERE processed = 0
                 AND retry_at IS NOT NULL
                 AND retry_at <= ?
                 AND retry_count < ?
               ORDER BY retry_at ASC
               LIMIT 50""",  # Procesar máximo 50 a la vez
            (now, MAX_RETRY_ATTEMPTS)
        ).fetchall()

    if not pending_webhooks:
        return 0

    logger.info(f"Procesando {len(pending_webhooks)} webhooks pendientes de reintento")

    for webhook in pending_webhooks:
        event_id = webhook["event_id"]
        provider = webhook["provider"]
        event_type = webhook["event_type"]
        retry_count = webhook["retry_count"]

        logger.info(f"Reintentando webhook {event_id} ({provider}/{event_type}), intento {retry_count + 1}")

        try:
            # Parsear payload
            import json
            payload = json.loads(webhook["payload"]) if isinstance(webhook["payload"], str) else eval(webhook["payload"])

            # Procesar según el proveedor
            success = False
            if provider == "stripe":
                from .payments.stripe_integration import stripe_service
                success = stripe_service.handle_webhook_event(payload, db_path)
            elif provider == "mercadopago":
                from .payments.mercadopago_integration import mercadopago_service
                success = mercadopago_service.handle_webhook_event(payload, db_path)

            if success:
                # Marcar como procesado
                with get_db(db_path) as conn:
                    conn.execute(
                        """UPDATE webhook_events
                           SET processed = 1,
                               processed_at = ?,
                               retry_at = NULL
                           WHERE event_id = ?""",
                        (datetime.now().isoformat(), event_id)
                    )
                successful_retries += 1
                logger.info(f"Webhook {event_id} procesado exitosamente en reintento {retry_count + 1}")
            else:
                # Programar siguiente reintento
                schedule_webhook_retry(event_id, provider, retry_count + 1, db_path)

        except Exception as e:
            logger.error(f"Error reintentando webhook {event_id}: {e}")
            # Programar siguiente reintento
            schedule_webhook_retry(event_id, provider, retry_count + 1, db_path)

    return successful_retries


def _mark_webhook_failed(event_id: str, db_path: str | None = None) -> None:
    """
    Marca un webhook como fallido permanentemente tras agotar reintentos.

    Args:
        event_id: ID del evento de webhook
        db_path: Ruta opcional a la base de datos (para tests)
    """
    with get_db(db_path) as conn:
        conn.execute(
            """UPDATE webhook_events
               SET processed = -1,
                   retry_at = NULL,
                   updated_at = ?
               WHERE event_id = ?""",
            (datetime.now().isoformat(), event_id)
        )

    logger.error(f"Webhook {event_id} marcado como fallido permanentemente")


def get_webhook_stats(db_path: str | None = None) -> dict:
    """
    Obtiene estadísticas de procesamiento de webhooks.

    Returns:
        Dict con estadísticas de webhooks
    """
    with get_db(db_path) as conn:
        # Total de webhooks
        total = conn.execute("SELECT COUNT(*) as count FROM webhook_events").fetchone()["count"]

        # Procesados exitosamente
        processed = conn.execute(
            "SELECT COUNT(*) as count FROM webhook_events WHERE processed = 1"
        ).fetchone()["count"]

        # Fallidos permanentemente
        failed = conn.execute(
            "SELECT COUNT(*) as count FROM webhook_events WHERE processed = -1"
        ).fetchone()["count"]

        # Pendientes de reintento
        pending_retry = conn.execute(
            "SELECT COUNT(*) as count FROM webhook_events WHERE processed = 0 AND retry_at IS NOT NULL"
        ).fetchone()["count"]

        # Sin procesar (primer intento fallido)
        unprocessed = conn.execute(
            "SELECT COUNT(*) as count FROM webhook_events WHERE processed = 0 AND retry_at IS NULL"
        ).fetchone()["count"]

    return {
        "total": total,
        "processed": processed,
        "failed": failed,
        "pending_retry": pending_retry,
        "unprocessed": unprocessed,
        "success_rate": (processed / total * 100) if total > 0 else 0,
    }
