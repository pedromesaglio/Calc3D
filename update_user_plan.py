#!/usr/bin/env python3
"""Script para asignar el plan 'Amigo de la casa' a un usuario específico"""
import sqlite3
from datetime import datetime

DB_PATH = "calc3d.db"
USERNAME = "Juangatti48"
NEW_PLAN = "friend"

def update_user_plan():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Buscar el usuario
    user = cursor.execute("SELECT id, username FROM users WHERE username = ?", (USERNAME,)).fetchone()

    if not user:
        print(f"❌ Usuario '{USERNAME}' no encontrado")
        conn.close()
        return

    user_id = user['id']
    print(f"✓ Usuario encontrado: {user['username']} (ID: {user_id})")

    # Verificar si tiene suscripción
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
        # Crear nueva suscripción
        cursor.execute("""
            INSERT INTO subscriptions
            (user_id, plan, status, started_at, created_at, updated_at)
            VALUES (?, ?, 'active', ?, ?, ?)
        """, (user_id, NEW_PLAN, now, now, now))
        print(f"✓ Suscripción creada con plan '{NEW_PLAN}'")

    conn.commit()

    # Verificar el cambio
    updated_sub = cursor.execute(
        "SELECT plan, status FROM subscriptions WHERE user_id = ?", (user_id,)
    ).fetchone()

    print(f"\n📋 Estado final:")
    print(f"   Usuario: {user['username']}")
    print(f"   Plan: {updated_sub['plan']}")
    print(f"   Estado: {updated_sub['status']}")
    print(f"\n✅ Plan 'Amigo de la casa' asignado correctamente!")

    conn.close()

if __name__ == "__main__":
    update_user_plan()
