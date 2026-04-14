#!/usr/bin/env python3
"""Script de utilidad para crear datos de prueba para comparaciones de precio.

Este script genera datos de precio de ayer basado en los datos de hoy,
introduciendo variaciones aleatorias de precio para simular cambios históricos.
Útil para probar la funcionalidad de comparación de precios.

Usage:
    python -m tracker.create_test_data
"""

from __future__ import annotations

import logging
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from tracker.schema import init_database

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DB_PATH: Path = Path("buscalibre_prices.sqlite")


def create_test_data(db_path: Path | None = None) -> None:
    """Crea datos de prueba para ayer basado en los precios de hoy.

    Lee los datos de precio de hoy desde la base de datos y crea los datos
    de ayer con variaciones aleatorias de precio (±10%). Usa INSERT OR REPLACE
    para asegurar ejecución idempotente.

    Args:
        db_path: Ruta a la base de datos. Usa DB_PATH por defecto.
    """
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    try:
        init_database(cursor)
        conn.commit()

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        logger.info("Fecha actual: %s", today)
        logger.info("Fecha ayer: %s", yesterday)

        cursor.execute(
            'SELECT title, price FROM book_prices WHERE date = ? LIMIT 5',
            (today,),
        )
        today_books = cursor.fetchall()

        if not today_books:
            logger.info("No hay datos de hoy para crear datos de prueba.")
            return

        logger.info(
            "Insertando datos de prueba para ayer basado en %d libros de hoy...",
            len(today_books),
        )

        for title, price in today_books:
            variation = random.uniform(-0.1, 0.1)
            yesterday_price = price * (1 + variation)

            cursor.execute(
                'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
                (title, yesterday_price, yesterday),
            )

            logger.info("  %s: Hoy=$%.2f, Ayer=$%.2f", title, price, yesterday_price)

        conn.commit()
        logger.info("Datos de prueba insertados correctamente.")

    except sqlite3.Error as e:
        logger.error("Error de base de datos: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    create_test_data()
