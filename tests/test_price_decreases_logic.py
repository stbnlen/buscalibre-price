"""Pruebas para la lógica de detección de disminuciones de precio"""

import pytest
import sqlite3
from datetime import date, timedelta

from tracker.price_tracker import PriceTracker, Product


class TestPriceDecreaseDetection:
    """Pruebas específicas para la lógica de detección de bajadas de precio"""

    def test_detects_simple_decrease(self, price_tracker):
        """Detecta una disminución simple de precio"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Precio ayer: 100, hoy: 80
        price_tracker.cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', ('Decreasing Book', 100.0, yesterday))
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Decreasing Book': Product(title='Decreasing Book', price=80.0)
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1
        decrease = price_tracker.price_decreases[0]
        assert decrease[0] == 'Decreasing Book'
        assert decrease[1] == 80.0   # current price
        assert decrease[2] == 100.0  # old price

    def test_detects_multiple_decreases(self, price_tracker):
        """Detecta múltiples disminuciones de precio"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', [
            ('Book A', 50.0, yesterday),
            ('Book B', 80.0, yesterday),
            ('Book C', 120.0, yesterday),
        ])
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Book A': Product(title='Book A', price=40.0),  # Bajó
            'Book B': Product(title='Book B', price=70.0),  # Bajó
            'Book C': Product(title='Book C', price=130.0),  # Subió
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 2
        decrease_titles = [d[0] for d in price_tracker.price_decreases]
        assert 'Book A' in decrease_titles
        assert 'Book B' in decrease_titles
        assert 'Book C' not in decrease_titles

    def test_no_decrease_when_price_same(self, price_tracker):
        """No registra disminución cuando el precio es igual"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', ('Stable Book', 50.0, yesterday))
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Stable Book': Product(title='Stable Book', price=50.0)
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 0

    def test_no_decrease_when_price_increased(self, price_tracker):
        """No registra disminución cuando el precio subió"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', ('Increasing Book', 50.0, yesterday))
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Increasing Book': Product(title='Increasing Book', price=60.0)
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 0

    def test_decrease_includes_historical_min(self, price_tracker):
        """La disminución incluye el precio mínimo histórico"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)

        # Insertar precios históricos
        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', [
            ('Historical Book', 90.0, last_week),  # Mínimo histórico
            ('Historical Book', 100.0, yesterday),
        ])
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Historical Book': Product(title='Historical Book', price=95.0)  # Bajó de ayer pero no es mínimo
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1
        decrease = price_tracker.price_decreases[0]
        assert decrease[3] == 90.0  # historical min

    def test_decrease_when_current_equals_historical_min(self, price_tracker):
        """Detecta disminución cuando el precio actual iguala el mínimo histórico"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        last_month = today - timedelta(days=30)

        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', [
            ('Min Book', 50.0, last_month),   # Mínimo histórico
            ('Min Book', 100.0, yesterday),
        ])
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Min Book': Product(title='Min Book', price=50.0)  # Igualó el mínimo
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1
        decrease = price_tracker.price_decreases[0]
        assert decrease[1] == 50.0   # current
        assert decrease[2] == 100.0  # yesterday
        assert decrease[3] == 50.0   # historical min

    def test_new_product_not_in_decreases(self, price_tracker):
        """Un producto nuevo no aparece en price_decreases"""
        price_tracker.current_data = {
            'Brand New Book': Product(title='Brand New Book', price=50.0)
        }

        price_tracker.compare_prices()

        # Debe aparecer en changes como "Nuevo producto"
        new_products = [c for c in price_tracker.changes if c[1] == "Nuevo producto"]
        assert len(new_products) == 1

        # Pero no en price_decreases
        assert len(price_tracker.price_decreases) == 0

    def test_decrease_difference_calculation(self, price_tracker):
        """Calcula correctamente la diferencia de precios"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', ('Diff Book', 100.0, yesterday))
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Diff Book': Product(title='Diff Book', price=75.50)
        }

        price_tracker.compare_prices()

        # En changes, la diferencia debe ser positiva (old - new)
        change = [c for c in price_tracker.changes if c[0] == 'Diff Book'][0]
        assert change[2] == 24.50  # 100.0 - 75.50

        # En price_decreases
        decrease = price_tracker.price_decreases[0]
        assert decrease[1] == 75.50   # current
        assert decrease[2] == 100.0   # old

    def test_small_decrease_detected(self, price_tracker):
        """Detecta incluso disminuciones pequeñas"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', ('Small Book', 10.01, yesterday))
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Small Book': Product(title='Small Book', price=10.00)
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1

    def test_price_decrease_with_many_history(self, price_tracker):
        """Maneja correctamente un largo historial de precios"""
        today = date.today()

        # Insertar 30 días de historial
        prices_history = []
        for days_ago in range(30, 0, -1):
            d = today - timedelta(days=days_ago)
            price = 100.0 + (days_ago * 0.5)  # Precios variados
            prices_history.append(('History Book', price, d))

        # Ayer precio alto
        yesterday = today - timedelta(days=1)
        prices_history.append(('History Book', 150.0, yesterday))

        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', prices_history)
        price_tracker.conn.commit()

        # Hoy bajó
        price_tracker.current_data = {
            'History Book': Product(title='History Book', price=80.0)
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1
        decrease = price_tracker.price_decreases[0]
        # El mínimo histórico debería ser alrededor de 100.5 (día 30)
        assert decrease[3] <= 101.0  # Mínimo histórico aproximado
