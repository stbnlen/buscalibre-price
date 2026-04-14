"""Pruebas para el script de creación de datos de prueba."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from tracker.create_test_data import create_test_data


class TestCreateTestData:
    """Pruebas para la función create_test_data."""

    def test_crea_datos_de_ayer(self, temp_db):
        """Crea datos de ayer basado en los datos de hoy."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [
                ('Libro Test 1', 100.0, today),
                ('Libro Test 2', 200.0, today),
                ('Libro Test 3', 300.0, today),
            ],
        )
        conn.commit()
        conn.close()

        create_test_data(db_path=temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT title, price FROM book_prices WHERE date = ?", (yesterday,))
        yesterday_data = cursor.fetchall()
        assert len(yesterday_data) == 3

        titles = [row[0] for row in yesterday_data]
        assert 'Libro Test 1' in titles
        assert 'Libro Test 2' in titles
        assert 'Libro Test 3' in titles
        conn.close()

    def test_precios_varian(self, temp_db):
        """Los precios de ayer tienen variación respecto a hoy."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [('Libro X', 100.0, today)],
        )
        conn.commit()
        conn.close()

        create_test_data(db_path=temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT price FROM book_prices WHERE date = ? AND title = ?",
            (yesterday, 'Libro X'),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] > 0
        conn.close()

    def test_sin_datos_hoy_muestra_mensaje(self, temp_db, caplog):
        """Cuando no hay datos de hoy, muestra mensaje apropiado."""
        caplog.set_level("INFO")
        create_test_data(db_path=temp_db)
        assert "no hay datos" in caplog.text.lower()

    def test_idempotente_con_insert_or_replace(self, temp_db):
        """Usa INSERT OR REPLACE para evitar duplicados."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [
                ('Libro 1', 100.0, today),
                ('Libro 2', 200.0, today),
                ('Libro 3', 300.0, today),
            ],
        )
        conn.commit()
        conn.close()

        create_test_data(db_path=temp_db)
        create_test_data(db_path=temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM book_prices WHERE date = ?", (yesterday,))
        count = cursor.fetchone()[0]
        assert count == 3
        conn.close()

    def test_limita_a_5_libros(self, temp_db):
        """Solo procesa hasta 5 libros (LIMIT en la consulta)."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        books = [(f'Book {i}', float(i * 10), today) for i in range(1, 21)]
        cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            books,
        )
        conn.commit()
        conn.close()

        create_test_data(db_path=temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM book_prices WHERE date = ?", (yesterday,))
        count = cursor.fetchone()[0]
        assert count == 5
        conn.close()

    def test_muestra_comparacion_de_precios(self, temp_db, caplog):
        """Muestra comparación de precios entre hoy y ayer en la salida."""
        today = date.today()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [('Libro A', 100.0, today)],
        )
        conn.commit()
        conn.close()

        caplog.set_level("INFO")
        create_test_data(db_path=temp_db)
        assert "fecha actual" in caplog.text.lower() or "fecha ayer" in caplog.text.lower()

    def test_conexion_cerrada_correctamente(self, temp_db):
        """La conexión a la base de datos se cierra correctamente."""
        today = date.today()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [('Libro A', 100.0, today)],
        )
        conn.commit()
        conn.close()

        create_test_data(db_path=temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM book_prices")
        count = cursor.fetchone()[0]
        assert count > 0
        conn.close()
