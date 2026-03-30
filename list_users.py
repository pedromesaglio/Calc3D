#!/usr/bin/env python3
"""Script para listar todos los usuarios de la base de datos"""
import sqlite3

DB_PATH = "calc3d.db"

def list_users():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Obtener todos los usuarios con su información de suscripción
    users = cursor.execute("""
        SELECT
            u.id,
            u.username,
            u.created_at,
            s.plan,
            s.status
        FROM users u
        LEFT JOIN subscriptions s ON u.id = s.user_id
        ORDER BY u.id
    """).fetchall()

    if not users:
        print("No hay usuarios en la base de datos")
        conn.close()
        return

    print(f"\n📋 Usuarios en la base de datos ({len(users)} total):\n")
    print(f"{'ID':<5} {'Username':<20} {'Plan':<20} {'Estado':<12} {'Creado':<20}")
    print("=" * 80)

    for user in users:
        user_id = user['id']
        username = user['username']
        plan = user['plan'] if user['plan'] else 'Sin plan'
        status = user['status'] if user['status'] else 'N/A'
        created = user['created_at'][:10] if user['created_at'] else 'N/A'

        print(f"{user_id:<5} {username:<20} {plan:<20} {status:<12} {created:<20}")

    conn.close()

if __name__ == "__main__":
    list_users()
