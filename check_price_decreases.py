#!/usr/bin/env python3
"""
Utility script to check for price decreases in the production database.

This is NOT a pytest test file. It's a diagnostic tool for checking
real price data.

Usage:
    python check_price_decreases.py
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

DB_PATH: Path = Path("buscalibre_prices.sqlite")


def check_price_decreases() -> None:
    """Check for price decreases in the production database."""
    if not DB_PATH.exists():
        logger.warning("Database not found at %s", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get today and yesterday
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        logger.info("Fecha actual: %s", today)
        logger.info("Fecha ayer: %s", yesterday)

        # Get today's prices
        cursor.execute('''
            SELECT title, price FROM book_prices WHERE date = ?
        ''', (today,))
        today_data = dict(cursor.fetchall())

        # Get yesterday's prices
        cursor.execute('''
            SELECT title, price FROM book_prices WHERE date = ?
        ''', (yesterday,))
        yesterday_data = dict(cursor.fetchall())

        # Get historical minimums
        cursor.execute('''
            SELECT title, MIN(price) FROM book_prices GROUP BY title
        ''')
        historical_mins = dict(cursor.fetchall())

        logger.info("\nLibros con datos de hoy: %d", len(today_data))
        logger.info("Libros con datos de ayer: %d", len(yesterday_data))

        # Find decreases
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
        logger.error("Database error: %s", e)
    finally:
        conn.close()


if __name__ == "__main__":
    check_price_decreases()
