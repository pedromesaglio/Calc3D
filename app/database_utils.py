"""
Utilidades para manejo de base de datos con transacciones atómicas
"""
from contextlib import contextmanager
from .db import get_db


@contextmanager
def atomic_transaction(db_path: str | None = None):
    """
    Context manager para transacciones atómicas en SQLite.

    Garantiza que todas las operaciones dentro del bloque se ejecuten
    como una sola unidad. Si ocurre un error, hace rollback automático.

    Uso:
        with atomic_transaction() as conn:
            conn.execute("INSERT INTO users ...")
            conn.execute("UPDATE subscriptions ...")
            # Si cualquiera falla, ambas se revierten

    Args:
        db_path: Ruta opcional a la base de datos (para tests)

    Yields:
        Connection: Conexión a la base de datos

    Raises:
        Exception: Cualquier excepción durante la transacción (tras rollback)
    """
    conn = get_db(db_path)

    try:
        # Iniciar transacción explícitamente
        conn.execute("BEGIN")
        yield conn
        # Si llegamos aquí, commit
        conn.commit()
    except Exception as e:
        # Si algo falló, rollback
        conn.rollback()
        raise e
    finally:
        # Siempre cerrar la conexión
        conn.close()
