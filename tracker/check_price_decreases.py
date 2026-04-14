#!/usr/bin/env python3
"""Script de utilidad para verificar disminuciones de precio en la base de datos de producción.

Este NO es un archivo de test de pytest. Es una herramienta de diagnóstico
para verificar datos de precios reales.

Usage:
    python -m tracker.check_price_decreases
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from tracker.schema import init_database

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

DB_PATH: Path = Path("buscalibre_prices.sqlite")


def check_price_decreases(db_path: Path | None = None) -> None:
    """Verifica disminuciones de precio en la base de datos de producción.

    Compara los precios de hoy con los de ayer e identifica libros
    cuyo precio haya disminuido, mostrando también el mínimo histórico.

    Args:
        db_path: Ruta a la base de datos. Usa DB_PATH por defecto.
    """
    path = db_path or DB_PATH

    if not path.exists():
        logger.warning("Base de datos no encontrada en %s", path)
        return

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
            'SELECT title, price FROM book_prices WHERE date = ?',
            (today,),
        )
        today_data = dict(cursor.fetchall())

        cursor.execute(
            'SELECT title, price FROM book_prices WHERE date = ?',
            (yesterday,),
        )
        yesterday_data = dict(cursor.fetchall())

        cursor.execute(
            'SELECT title, MIN(price) FROM book_prices GROUP BY title'
        )
        historical_mins = dict(cursor.fetchall())

        logger.info("\nLibros con datos de hoy: %d", len(today_data))
        logger.info("Libros con datos de ayer: %d", len(yesterday_data))

        decreases = []
        for title, current_price in today_data.items():
            if title in yesterday_data:
                old_price = yesterday_data[title]
                historical_min = historical_mins.get(title, 0)

                if current_price < old_price:
                    decreases.append((title, current_price, old_price, historical_min))

        logger.info("\nLibros con precio disminuido: %d", len(decreases))

        if decreases:
            print("\n" + "=" * 90)
            print("LIBROS CON PRECIO DISMINUIDO RESPECTO AL DÍA ANTERIOR:")
            print("=" * 90)
            for title, current_price, previous_price, historical_min in decreases[:10]:
                print(f"Título: {title}")
                print(f"  Precio actual: ${current_price:,.2f}")
                print(f"  Precio del día anterior: ${previous_price:,.2f}")
                print(f"  Precio mínimo histórico: ${historical_min:,.2f}")
                print()
        else:
            print("No se encontraron libros con precio disminuido respecto al día anterior.")

    except sqlite3.Error as e:
        logger.error("Error de base de datos: %s", e)
    finally:
        conn.close()


if __name__ == "__main__":
    check_price_decreases()
