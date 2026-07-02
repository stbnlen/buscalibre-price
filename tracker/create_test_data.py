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
from datetime import date, timedelta
from pathlib import Path

from tracker.config import DEFAULT_DB_PATH
from tracker.repository import PriceRepository

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Fixed seed so test runs are deterministic.
DEFAULT_SEED = 42
DEFAULT_LIMIT = 5


def create_test_data(
    db_path: Path | None = None,
    seed: int = DEFAULT_SEED,
    limit: int = DEFAULT_LIMIT,
) -> None:
    """Crea datos de prueba para ayer basado en los precios de hoy.

    Lee los datos de precio de hoy desde la base de datos y crea los datos
    de ayer con variaciones aleatorias de precio (±10%). Usa INSERT OR REPLACE
    para asegurar ejecución idempotente.

    Args:
        db_path: Ruta a la base de datos. Usa ``DEFAULT_DB_PATH`` por defecto.
        seed: Semilla para el generador aleatorio. Por defecto 42.
        limit: Máximo de libros a procesar. Por defecto 5.
    """
    path = db_path or DEFAULT_DB_PATH
    rng = random.Random(seed)

    today = date.today()
    yesterday = today - timedelta(days=1)

    logger.info("Fecha actual: %s", today)
    logger.info("Fecha ayer: %s", yesterday)

    with PriceRepository(path) as repository:
        today_books = list(repository.get_prices_for_date(today).items())[
            :limit
        ]

        if not today_books:
            logger.info("No hay datos de hoy para crear datos de prueba.")
            return

        logger.info(
            "Insertando datos de prueba para ayer basado en %d libros de hoy...",
            len(today_books),
        )

        for title, price in today_books:
            variation = rng.uniform(-0.1, 0.1)
            yesterday_price = price * (1 + variation)
            repository.save_price(title, yesterday_price, yesterday)
            logger.info(
                "  %s: Hoy=$%.2f, Ayer=$%.2f", title, price, yesterday_price
            )

    logger.info("Datos de prueba insertados correctamente.")


if __name__ == "__main__":
    create_test_data()
