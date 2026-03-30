#!/usr/bin/env python3
"""Script para crear un usuario con el plan 'Amigo de la casa'"""
import sqlite3
from datetime import datetime, timedelta
import hashlib

DB_PATH = "calc3d.db"
USERNAME = "Juangatti48"
PASSWORD = "Losgatti10"
NEW_PLAN = "friend"

def hash_password(password: str) -> str:
    """Hash de contraseña usando SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_friend_user():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Verificar si el usuario ya existe
    existing_user = cursor.execute(
        "SELECT id, username FROM users WHERE username = ?", (USERNAME,)
    ).fetchone()

    if existing_user:
        print(f"✓ Usuario '{USERNAME}' ya existe (ID: {existing_user['id']})")
        user_id = existing_user['id']
    else:
        # Crear nuevo usuario
        now = datetime.now().isoformat()
        password_hash = hash_password(PASSWORD)

        cursor.execute("""
            INSERT INTO users (username, password_hash, created_at)
            VALUES (?, ?, ?)
        """, (USERNAME, password_hash, now))

        user_id = cursor.lastrowid
        print(f"✓ Usuario creado: {USERNAME} (ID: {user_id})")

    # Verificar/crear suscripción
    subscription = cursor.execute(
        "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
    ).fetchone()

    now = datetime.now().isoformat()

    if subscription:
        # Actualizar plan existente
        old_plan = subscription['plan']
        cursor.execute(
            "UPDATE subscriptions SET plan = ?, updated_at = ? WHERE user_id = ?",
            (NEW_PLAN, now, user_id)
        )
        print(f"✓ Plan actualizado: '{old_plan}' → '{NEW_PLAN}'")
    else:
        # Crear nueva suscripción con plan "friend"
        cursor.execute("""
            INSERT INTO subscriptions
            (user_id, plan, status, started_at, created_at, updated_at)
            VALUES (?, ?, 'active', ?, ?, ?)
        """, (user_id, NEW_PLAN, now, now, now))
        print(f"✓ Suscripción creada con plan '{NEW_PLAN}'")

    # Verificar/crear límites de uso
    usage = cursor.execute(
        "SELECT * FROM usage_limits WHERE user_id = ?", (user_id,)
    ).fetchone()

    if not usage:
        next_reset = (datetime.now() + timedelta(days=30)).isoformat()
        cursor.execute("""
            INSERT INTO usage_limits
            (user_id, reset_at, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, next_reset, now, now))
        print(f"✓ Límites de uso creados")

    conn.commit()

    # Mostrar información final
    print(f"\n📋 Usuario configurado:")
    print(f"   Username: {USERNAME}")
    print(f"   Password: {PASSWORD}")
    print(f"   Plan: Amigo de la casa")
    print(f"   Límites:")
    print(f"     - 30 cálculos/mes")
    print(f"     - 50 presupuestos/mes")
    print(f"     - 50 clientes")
    print(f"     - 50 piezas en catálogo")
    print(f"\n✅ Usuario listo para usar!")

    conn.close()

if __name__ == "__main__":
    create_friend_user()
