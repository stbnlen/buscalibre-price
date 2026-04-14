"""Pruebas para el script de verificación de disminuciones de precio."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from tracker.check_price_decreases import check_price_decreases


class TestCheckPriceDecreases:
    """Pruebas para la función check_price_decreases."""

    def test_base_datos_no_existente(self, tmp_path, caplog):
        """Muestra warning cuando la base de datos no existe."""
        caplog.set_level("WARNING")
        nonexistent = tmp_path / "no_existe.sqlite"
        check_price_decreases(db_path=nonexistent)
        assert "no encontrada" in caplog.text.lower()

    def test_sin_disminuciones(self, temp_db, capsys):
        """Muestra mensaje cuando no hay disminuciones."""
        check_price_decreases(db_path=temp_db)
        captured = capsys.readouterr()
        assert "No se encontraron" in captured.out

    def test_con_disminuciones(self, temp_db, capsys):
        """Muestra libros con precio disminuido."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [('Book A', 100.0, yesterday), ('Book A', 80.0, today)],
        )
        conn.commit()
        conn.close()

        check_price_decreases(db_path=temp_db)
        captured = capsys.readouterr()
        assert "Book A" in captured.out
        assert "DISMINUIDO" in captured.out

    def test_sin_datos_de_hoy(self, temp_db, capsys):
        """Muestra mensaje cuando no hay datos de hoy."""
        yesterday = date.today() - timedelta(days=1)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            ('Book A', 100.0, yesterday),
        )
        conn.commit()
        conn.close()

        check_price_decreases(db_path=temp_db)
        captured = capsys.readouterr()
        assert "No se encontraron" in captured.out

    def test_precio_subido_no_mostrado(self, temp_db, capsys):
        """No muestra libros cuyo precio subió."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [('Book B', 80.0, yesterday), ('Book B', 100.0, today)],
        )
        conn.commit()
        conn.close()

        check_price_decreases(db_path=temp_db)
        captured = capsys.readouterr()
        assert "Book B" not in captured.out
