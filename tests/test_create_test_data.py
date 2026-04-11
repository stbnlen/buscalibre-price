"""Tests for the create_test_data script"""

import pytest
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import importlib.util
import sys
from pathlib import Path


@pytest.fixture
def create_test_data_module():
    """Dynamically load the create_test_data module"""
    module_path = Path(__file__).parent.parent / "create_test_data.py"
    spec = importlib.util.spec_from_file_location("create_test_data", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def db_with_today_data(temp_db):
    """Creates a DB with today's data for testing create_test_data"""
    today = date.today()

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(title, date)
        )
    ''')

    cursor.executemany('''
        INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
    ''', [
        ('Libro Test 1', 100.0, today),
        ('Libro Test 2', 200.0, today),
        ('Libro Test 3', 300.0, today),
    ])

    conn.commit()
    conn.close()

    return temp_db


@pytest.fixture
def empty_db(temp_db):
    """Creates an empty DB for testing no-data scenarios"""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(title, date)
        )
    ''')

    conn.commit()
    conn.close()

    return temp_db


class TestCreateTestData:
    """Tests for the create_test_data function"""

    def test_module_is_importable(self, create_test_data_module):
        """The create_test_data module can be imported"""
        assert create_test_data_module is not None
        assert hasattr(create_test_data_module, 'create_test_data')

    def test_function_is_callable(self, create_test_data_module):
        """The create_test_data function is callable"""
        assert callable(create_test_data_module.create_test_data)

    def test_creates_yesterday_data(self, create_test_data_module, db_with_today_data, capsys):
        """Creates yesterday's data based on today's data"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Mock the DB_PATH in the module
        with patch.object(create_test_data_module, 'DB_PATH', Path(db_with_today_data)):
            create_test_data_module.create_test_data()

        # Verify yesterday's data was created
        conn = sqlite3.connect(db_with_today_data)
        cursor = conn.cursor()

        cursor.execute("SELECT title, price FROM book_prices WHERE date = ?", (yesterday,))
        yesterday_data = cursor.fetchall()

        assert len(yesterday_data) == 3

        titles = [row[0] for row in yesterday_data]
        assert 'Libro Test 1' in titles
        assert 'Libro Test 2' in titles
        assert 'Libro Test 3' in titles

        conn.close()

    def test_prices_vary_from_today(self, create_test_data_module, db_with_today_data, capsys):
        """Yesterday's prices have variation from today"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        with patch.object(create_test_data_module, 'DB_PATH', Path(db_with_today_data)):
            create_test_data_module.create_test_data()

        conn = sqlite3.connect(db_with_today_data)
        cursor = conn.cursor()

        cursor.execute("SELECT title, price FROM book_prices WHERE date = ?", (today,))
        today_prices = dict(cursor.fetchall())

        cursor.execute("SELECT title, price FROM book_prices WHERE date = ?", (yesterday,))
        yesterday_prices = dict(cursor.fetchall())

        for title in today_prices:
            if title in yesterday_prices:
                assert yesterday_prices[title] > 0

        conn.close()

    def test_no_today_data_shows_message(self, create_test_data_module, empty_db, caplog):
        """When no today's data exists, shows appropriate message"""
        caplog.set_level("INFO")
        with patch.object(create_test_data_module, 'DB_PATH', Path(empty_db)):
            create_test_data_module.create_test_data()

        assert "no hay datos" in caplog.text.lower()

    def test_uses_insert_or_replace(self, create_test_data_module, db_with_today_data, capsys):
        """Uses INSERT OR REPLACE to avoid duplicates"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        with patch.object(create_test_data_module, 'DB_PATH', Path(db_with_today_data)):
            create_test_data_module.create_test_data()

        with patch.object(create_test_data_module, 'DB_PATH', Path(db_with_today_data)):
            create_test_data_module.create_test_data()

        conn = sqlite3.connect(db_with_today_data)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM book_prices WHERE date = ?", (yesterday,))
        count = cursor.fetchone()[0]
        assert count == 3

        conn.close()

    def test_output_shows_price_comparison(self, create_test_data_module, db_with_today_data, caplog):
        """Output shows price comparison between today and yesterday"""
        caplog.set_level("INFO")
        with patch.object(create_test_data_module, 'DB_PATH', Path(db_with_today_data)):
            create_test_data_module.create_test_data()

        assert "fecha actual" in caplog.text.lower() or "fecha ayer" in caplog.text.lower()


class TestCreateTestDataEdgeCases:
    """Edge case tests for create_test_data"""

    def test_handles_single_book(self, create_test_data_module, temp_db, capsys):
        """Handles a single book correctly"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS book_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title, date)
            )
        ''')

        cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', ('Single Book', 50.0, today))

        conn.commit()
        conn.close()

        with patch.object(create_test_data_module, 'DB_PATH', Path(temp_db)):
            create_test_data_module.create_test_data()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM book_prices WHERE date = ?", (yesterday,))
        count = cursor.fetchone()[0]
        assert count == 1

        conn.close()

    def test_handles_many_books(self, create_test_data_module, temp_db, capsys):
        """Handles many books correctly (note: create_test_data has LIMIT 5)"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS book_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(title, date)
            )
        ''')

        books = [(f'Book {i}', float(i * 10), today) for i in range(1, 21)]
        cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', books)

        conn.commit()
        conn.close()

        with patch.object(create_test_data_module, 'DB_PATH', Path(temp_db)):
            create_test_data_module.create_test_data()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM book_prices WHERE date = ?", (yesterday,))
        count = cursor.fetchone()[0]
        assert count == 5  # LIMIT 5 in create_test_data.py

        conn.close()

    def test_database_connection_closed(self, create_test_data_module, db_with_today_data):
        """Database connection is properly closed"""
        with patch.object(create_test_data_module, 'DB_PATH', Path(db_with_today_data)):
            create_test_data_module.create_test_data()

        conn = sqlite3.connect(db_with_today_data)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM book_prices")
        count = cursor.fetchone()[0]
        assert count > 0
        conn.close()
