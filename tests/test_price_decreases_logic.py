"""Pruebas para la lógica de detección de disminuciones de precio"""

import pytest
from datetime import date, timedelta

from tracker.price_tracker import PriceTracker
from tracker.models import Product


class TestPriceDecreaseDetection:
    """Pruebas específicas para la lógica de detección de bajadas de precio."""

    def test_detecta_disminucion_simple(self, price_tracker):
        """Detecta una disminución simple de precio."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            ('Decreasing Book', 100.0, yesterday),
        )
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Decreasing Book': Product(title='Decreasing Book', price=80.0),
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1
        decrease = price_tracker.price_decreases[0]
        assert decrease[0] == 'Decreasing Book'
        assert decrease[1] == 80.0
        assert decrease[2] == 100.0

    def test_detecta_multiples_disminuciones(self, price_tracker):
        """Detecta múltiples disminuciones de precio."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [
                ('Book A', 50.0, yesterday),
                ('Book B', 80.0, yesterday),
                ('Book C', 120.0, yesterday),
            ],
        )
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Book A': Product(title='Book A', price=40.0),
            'Book B': Product(title='Book B', price=70.0),
            'Book C': Product(title='Book C', price=130.0),
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 2
        decrease_titles = [d[0] for d in price_tracker.price_decreases]
        assert 'Book A' in decrease_titles
        assert 'Book B' in decrease_titles
        assert 'Book C' not in decrease_titles

    def test_sin_disminucion_precio_igual(self, price_tracker):
        """No registra disminución cuando el precio es igual."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            ('Stable Book', 50.0, yesterday),
        )
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Stable Book': Product(title='Stable Book', price=50.0),
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 0

    def test_sin_disminucion_precio_subio(self, price_tracker):
        """No registra disminución cuando el precio subió."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            ('Increasing Book', 50.0, yesterday),
        )
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Increasing Book': Product(title='Increasing Book', price=60.0),
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 0

    def test_disminucion_incluye_minimo_historico(self, price_tracker):
        """La disminución incluye el precio mínimo histórico."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)

        price_tracker.cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [
                ('Historical Book', 90.0, last_week),
                ('Historical Book', 100.0, yesterday),
            ],
        )
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Historical Book': Product(title='Historical Book', price=95.0),
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1
        decrease = price_tracker.price_decreases[0]
        assert decrease[3] == 90.0

    def test_disminucion_iguala_minimo_historico(self, price_tracker):
        """Detecta disminución cuando el precio actual iguala el mínimo histórico."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        last_month = today - timedelta(days=30)

        price_tracker.cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            [
                ('Min Book', 50.0, last_month),
                ('Min Book', 100.0, yesterday),
            ],
        )
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Min Book': Product(title='Min Book', price=50.0),
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1
        decrease = price_tracker.price_decreases[0]
        assert decrease[1] == 50.0
        assert decrease[2] == 100.0
        assert decrease[3] == 50.0

    def test_producto_nuevo_no_en_disminuciones(self, price_tracker):
        """Un producto nuevo no aparece en price_decreases."""
        price_tracker.current_data = {
            'Brand New Book': Product(title='Brand New Book', price=50.0),
        }

        price_tracker.compare_prices()

        new_products = [c for c in price_tracker.changes if c[1] == "Nuevo producto"]
        assert len(new_products) == 1
        assert len(price_tracker.price_decreases) == 0

    def test_calculo_diferencia_de_precios(self, price_tracker):
        """Calcula correctamente la diferencia de precios."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            ('Diff Book', 100.0, yesterday),
        )
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Diff Book': Product(title='Diff Book', price=75.50),
        }

        price_tracker.compare_prices()

        change = [c for c in price_tracker.changes if c[0] == 'Diff Book'][0]
        assert change[2] == 24.50

        decrease = price_tracker.price_decreases[0]
        assert decrease[1] == 75.50
        assert decrease[2] == 100.0

    def test_detecta_disminucion_pequena(self, price_tracker):
        """Detecta incluso disminuciones pequeñas."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            ('Small Book', 10.01, yesterday),
        )
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Small Book': Product(title='Small Book', price=10.00),
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1

    def test_historial_largo_de_precios(self, price_tracker):
        """Maneja correctamente un largo historial de precios."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        prices_history = []
        for days_ago in range(30, 0, -1):
            d = today - timedelta(days=days_ago)
            price = 100.0 + (days_ago * 0.5)
            prices_history.append(('History Book', price, d))

        prices_history.append(('History Book', 150.0, yesterday))

        price_tracker.cursor.executemany(
            'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
            prices_history,
        )
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'History Book': Product(title='History Book', price=80.0),
        }

        price_tracker.compare_prices()

        assert len(price_tracker.price_decreases) == 1
        decrease = price_tracker.price_decreases[0]
        assert decrease[3] <= 101.0


class TestPriceDecreaseLogicWithData:
    """Pruebas de la lógica de disminuciones usando datos de muestra."""

    def test_detecta_disminucion_correcta(self, sample_price_data):
        """Prueba que detecta correctamente las disminuciones de precio."""
        today_data = sample_price_data['today']
        yesterday_data = sample_price_data['yesterday']
        historical_mins = sample_price_data['historical_mins']

        decreases = []
        for title, current_price in today_data.items():
            if title in yesterday_data:
                old_price = yesterday_data[title]
                historical_min = historical_mins.get(title, 0)
                if current_price < old_price:
                    decreases.append((title, current_price, old_price, historical_min))

        assert len(decreases) == 1
        assert decreases[0][0] == 'Libro A'
        assert decreases[0][1] == 20.00
        assert decreases[0][2] == 25.00
        assert decreases[0][3] == 18.00

    def test_sin_disminuciones_precios_iguales_o_mayores(self, sample_price_data):
        """No detecta disminuciones cuando los precios son iguales o mayores."""
        today_data = {
            'Libro A': 25.00,
            'Libro B': 20.00,
            'Libro C': 35.00,
        }
        yesterday_data = sample_price_data['yesterday']
        historical_mins = sample_price_data['historical_mins']

        decreases = []
        for title, current_price in today_data.items():
            if title in yesterday_data:
                old_price = yesterday_data[title]
                if current_price < old_price:
                    decreases.append((title, current_price, old_price, historical_mins.get(title, 0)))

        assert len(decreases) == 0

    def test_maneja_datos_de_ayer_faltantes(self, sample_price_data):
        """Maneja correctamente cuando no hay datos de ayer para un libro."""
        today_data = sample_price_data['today']
        yesterday_data = {'Libro X': 10.00}
        historical_mins = sample_price_data['historical_mins']

        decreases = []
        for title, current_price in today_data.items():
            if title in yesterday_data:
                old_price = yesterday_data[title]
                if current_price < old_price:
                    decreases.append((title, current_price, old_price, historical_mins.get(title, 0)))

        assert len(decreases) == 0
