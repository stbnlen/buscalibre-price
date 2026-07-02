#!/usr/bin/env python3
"""Script de utilidad para verificar disminuciones de precio en la base de datos.

Este NO es un archivo de test de pytest. Es una herramienta de diagnóstico
para verificar datos de precios reales.

Usage:
    python -m tracker.check_price_decreases
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

from tracker.analyzer import detect_decreases_between_dates
from tracker.config import DEFAULT_DB_PATH
from tracker.repository import PriceRepository
from tracker.reporter import format_check_decreases

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def check_price_decreases(db_path: Path | None = None) -> str:
    """Verifica disminuciones de precio en la base de datos de producción.

    Compara los precios de hoy con los de ayer e identifica libros
    cuyo precio haya disminuido, mostrando también el mínimo histórico.

    Args:
        db_path: Ruta a la base de datos. Usa ``DEFAULT_DB_PATH`` por defecto.

    Returns:
        Reporte formateado como string.
    """
    path = db_path or DEFAULT_DB_PATH

    if not path.exists():
        message = f"Base de datos no encontrada en {path}"
        logger.warning(message)
        return message

    today = date.today()
    yesterday = today - timedelta(days=1)

    with PriceRepository(path) as repository:
        today_data = repository.get_prices_for_date(today)
        yesterday_data = repository.get_prices_for_date(yesterday)
        historical_mins = repository.get_historical_mins()

    logger.info("Fecha actual: %s", today)
    logger.info("Fecha ayer: %s", yesterday)
    logger.info("\nLibros con datos de hoy: %d", len(today_data))
    logger.info("Libros con datos de ayer: %d", len(yesterday_data))

    decreases = detect_decreases_between_dates(
        today_data, yesterday_data, historical_mins
    )

    logger.info("\nLibros con precio disminuido: %d", len(decreases))
    return format_check_decreases(decreases)


if __name__ == "__main__":
    print(check_price_decreases())
