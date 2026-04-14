"""Configuración y fixtures para los tests de pytest"""

import os
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from tracker.models import Product
from tracker.price_tracker import PriceTracker
from tracker.schema import init_database


@pytest.fixture
def temp_db_path():
    """Creates a temporary database path without initializing tables"""
    fd, db_path = tempfile.mkstemp(suffix='.sqlite')
    os.close(fd)
    yield Path(db_path)
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def temp_db(temp_db_path):
    """Crea una base de datos temporal con tablas inicializadas."""
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    init_database(cursor)
    conn.commit()
    conn.close()

    yield temp_db_path


@pytest.fixture
def db_connection(temp_db):
    """Provides a database connection for tests"""
    conn = sqlite3.connect(temp_db)
    yield conn
    conn.close()


@pytest.fixture
def price_tracker(temp_db, monkeypatch):
    """Creates a PriceTracker with a temporary database"""
    # Create tracker with temp db path
    tracker = PriceTracker(db_path=temp_db)

    yield tracker

    # Cleanup
    tracker.close()


@pytest.fixture
def price_tracker_with_data(price_tracker):
    """Creates a PriceTracker with pre-loaded test data"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    # Data from two days ago (base prices)
    price_tracker.cursor.executemany('''
        INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
    ''', [
        ('Libro A', 22.00, two_days_ago),
        ('Libro B', 14.00, two_days_ago),
        ('Libro C', 28.00, two_days_ago),
    ])

    # Data from yesterday (higher prices)
    price_tracker.cursor.executemany('''
        INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
    ''', [
        ('Libro A', 25.00, yesterday),
        ('Libro B', 15.50, yesterday),
        ('Libro C', 30.00, yesterday),
    ])

    # Today's data (some prices decreased)
    price_tracker.current_data = {
        'Libro A': Product(title='Libro A', price=20.00),  # Decreased from 25.00
        'Libro B': Product(title='Libro B', price=15.50),  # Same
        'Libro C': Product(title='Libro C', price=35.00),  # Increased from 30.00
        'Libro D': Product(title='Libro D', price=12.00),  # New
    }

    price_tracker.conn.commit()
    return price_tracker


@pytest.fixture
def sample_price_data():
    """Sample price data for tests that don't need a database"""
    return {
        'today': {
            'Libro A': 20.00,
            'Libro B': 15.50,
            'Libro C': 35.00,
            'Libro D': 12.00
        },
        'yesterday': {
            'Libro A': 25.00,
            'Libro B': 15.50,
            'Libro C': 30.00
        },
        'historical_mins': {
            'Libro A': 18.00,
            'Libro B': 14.00,
            'Libro C': 28.00,
            'Libro D': 12.00
        }
    }


@pytest.fixture
def sample_products():
    """Sample products for tests"""
    return {
        'Libro A': Product(title='Libro A', price=20.00),
        'Libro B': Product(title='Libro B', price=15.50),
        'Libro C': Product(title='Libro C', price=35.00),
        'Libro D': Product(title='Libro D', price=12.00),
    }
