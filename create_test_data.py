#!/usr/bin/env python3
"""Utility script to create test data for price comparisons.

This script generates yesterday's price data based on today's data,
introducing random price variations to simulate historical price changes.
Useful for testing price comparison functionality.

Usage:
    python create_test_data.py
"""

import logging
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Constants
DB_PATH: Path = Path("buscalibre_prices.sqlite")


def create_test_data() -> None:
    """Create test data for yesterday based on today's prices.

    Reads today's price data from the database and creates yesterday's
    data with random price variations (±10%). Uses INSERT OR REPLACE
    to ensure idempotent execution.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get today and yesterday
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        logger.info("Fecha actual: %s", today)
        logger.info("Fecha ayer: %s", yesterday)

        # Check if we have any books in today's data
        cursor.execute('''
            SELECT title, price FROM book_prices WHERE date = ? LIMIT 5
        ''', (today,))
        today_books = cursor.fetchall()

        if not today_books:
            logger.info("No hay datos de hoy para crear datos de prueba.")
            return

        logger.info(
            "Insertando datos de prueba para ayer basado en %d libros de hoy...",
            len(today_books)
        )

        # Insert yesterday's data with slightly modified prices
        for title, price in today_books:
            # Vary the price ±10%
            variation = random.uniform(-0.1, 0.1)
            yesterday_price = price * (1 + variation)

            # Insert yesterday's price
            cursor.execute('''
                INSERT OR REPLACE INTO book_prices (title, price, date)
                VALUES (?, ?, ?)
            ''', (title, yesterday_price, yesterday))

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
