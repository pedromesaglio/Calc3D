"""Rutas administrativas (solo para desarrollo/setup inicial)"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import hashlib
from datetime import datetime, timedelta
from ..db import get_db

router = APIRouter()


@router.post("/admin/setup-friend-user")
async def setup_friend_user():
    """Crea el usuario 'Amigo de la casa' - Solo usar una vez"""
    USERNAME = "juangatti48"
    PASSWORD = "Losgatti10"
    PLAN = "friend"

    try:
        password_hash = hashlib.sha256(PASSWORD.encode()).hexdigest()

        with get_db() as conn:
            # Verificar si existe
            user = conn.execute(
                "SELECT id FROM users WHERE username = ?", (USERNAME,)
            ).fetchone()

            if user:
                user_id = user[0]
                # Actualizar contraseña
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (password_hash, user_id)
                )
                message = f"Usuario {USERNAME} actualizado (contraseña reseteada)"
            else:
                # Crear usuario
                now = datetime.now().isoformat()
                cursor = conn.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (USERNAME, password_hash, now)
                )
                user_id = cursor.lastrowid
                message = f"Usuario {USERNAME} creado"

            # Crear/actualizar suscripción
            now = datetime.now().isoformat()
            subscription = conn.execute(
                "SELECT id FROM subscriptions WHERE user_id = ?", (user_id,)
            ).fetchone()

            if subscription:
                conn.execute(
                    "UPDATE subscriptions SET plan = ?, status = 'active', updated_at = ? WHERE user_id = ?",
                    (PLAN, now, user_id)
                )
            else:
                conn.execute(
                    """INSERT INTO subscriptions
                       (user_id, plan, status, started_at, created_at, updated_at)
                       VALUES (?, ?, 'active', ?, ?, ?)""",
                    (user_id, PLAN, now, now, now)
                )

            # Crear/resetear límites
            usage = conn.execute(
                "SELECT id FROM usage_limits WHERE user_id = ?", (user_id,)
            ).fetchone()

            next_reset = (datetime.now() + timedelta(days=30)).isoformat()
            if usage:
                conn.execute(
                    """UPDATE usage_limits SET
                       calculations_used = 0, quotes_used = 0,
                       clients_used = 0, catalog_items_used = 0,
                       reset_at = ?, updated_at = ?
                       WHERE user_id = ?""",
                    (next_reset, now, user_id)
                )
            else:
                conn.execute(
                    """INSERT INTO usage_limits
                       (user_id, reset_at, created_at, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (user_id, next_reset, now, now)
                )

        return JSONResponse({
            "success": True,
            "message": message,
            "user_id": user_id,
            "username": USERNAME,
            "password": PASSWORD,
            "plan": PLAN,
            "limits": {
                "calculations": 30,
                "quotes": 50,
                "clients": 50,
                "catalog_items": 50
            }
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
