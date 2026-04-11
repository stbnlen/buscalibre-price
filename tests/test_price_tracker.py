"""Pruebas comprehensivas para la clase PriceTracker"""

import pytest
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from tracker.price_tracker import PriceTracker, Product


class TestProduct:
    """Pruebas para la clase Product"""

    def test_product_creation(self):
        """Se puede crear un producto correctamente"""
        product = Product(title="Test Book", price=100.0)
        assert product.title == "Test Book"
        assert product.price == 100.0

    def test_product_equality(self):
        """Dos productos con mismos datos son iguales"""
        p1 = Product(title="Book", price=50.0)
        p2 = Product(title="Book", price=50.0)
        assert p1 == p2

    def test_product_inequality(self):
        """Productos con distintos datos no son iguales"""
        p1 = Product(title="Book A", price=50.0)
        p2 = Product(title="Book B", price=50.0)
        assert p1 != p2


class TestPriceTrackerInit:
    """Tests for PriceTracker initialization"""

    def test_init_creates_database(self, temp_db_path):
        """Initialization creates the database and tables"""
        tracker = PriceTracker(db_path=temp_db_path)

        # Verify tables exist
        tracker.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='book_prices'"
        )
        assert tracker.cursor.fetchone() is not None

        tracker.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='price_changes'"
        )
        assert tracker.cursor.fetchone() is not None

        tracker.close()

    def test_init_default_values(self):
        """Default values are initialized correctly"""
        tracker = PriceTracker()
        assert tracker.current_data == {}
        assert tracker.changes == []
        assert tracker.price_decreases == []
        tracker.close()


class TestComparePrices:
    """Pruebas para el método compare_prices"""

    def test_price_decreased(self, price_tracker_with_data):
        """Detecta cuando un precio bajó"""
        tracker = price_tracker_with_data
        changes = tracker.compare_prices()

        # Libro A bajó de 25.00 a 20.00
        libro_a_change = [c for c in changes if c[0] == 'Libro A'][0]
        assert libro_a_change[1] == "Bajó"
        assert libro_a_change[2] == 5.00  # difference
        assert libro_a_change[3] == 20.00  # new_price

    def test_price_increased(self, price_tracker_with_data):
        """Detecta cuando un precio subió"""
        tracker = price_tracker_with_data
        changes = tracker.compare_prices()

        # Libro C subió de 30.00 a 35.00
        libro_c_change = [c for c in changes if c[0] == 'Libro C'][0]
        assert libro_c_change[1] == "Subió"
        assert libro_c_change[2] == 5.00
        assert libro_c_change[3] == 35.00

    def test_price_unchanged(self, price_tracker_with_data):
        """No registra cambios cuando el precio es igual"""
        tracker = price_tracker_with_data
        changes = tracker.compare_prices()

        # Libro B tiene el mismo precio
        libro_b_changes = [c for c in changes if c[0] == 'Libro B']
        assert len(libro_b_changes) == 0

    def test_new_product(self, price_tracker_with_data):
        """Detecta cuando un producto es nuevo"""
        tracker = price_tracker_with_data
        changes = tracker.compare_prices()

        # Libro D es nuevo
        libro_d_change = [c for c in changes if c[0] == 'Libro D'][0]
        assert libro_d_change[1] == "Nuevo producto"

    def test_price_decreases_populated(self, price_tracker_with_data):
        """La lista price_decreases se llena correctamente"""
        tracker = price_tracker_with_data
        tracker.compare_prices()

        # Solo Libro A bajó
        assert len(tracker.price_decreases) == 1
        decrease = tracker.price_decreases[0]
        assert decrease[0] == 'Libro A'
        assert decrease[1] == 20.00  # current price
        assert decrease[2] == 25.00  # old price

    def test_compare_returns_list(self, price_tracker_with_data):
        """compare_prices retorna una lista"""
        result = price_tracker_with_data.compare_prices()
        assert isinstance(result, list)

    def test_compare_persists_to_database(self, price_tracker_with_data):
        """Los cambios se guardan en la base de datos"""
        tracker = price_tracker_with_data
        tracker.compare_prices()

        tracker.cursor.execute("SELECT COUNT(*) FROM price_changes")
        count = tracker.cursor.fetchone()[0]
        # Debe haber 3 cambios: Libro A (bajó), Libro C (subió), Libro D (nuevo)
        assert count == 3


class TestHistoricalMinPrice:
    """Pruebas para get_books_with_historical_min_price"""

    def test_no_data_returns_empty(self, price_tracker):
        """Sin datos retorna lista vacía"""
        result = price_tracker.get_books_with_historical_min_price()
        assert result == []

    def test_current_is_historical_min(self, price_tracker):
        """Detecta cuando el precio actual es el mínimo histórico"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Insertar precios: ayer más alto, hoy mínimo
        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', [
            ('Book Min', 100.0, yesterday),
            ('Book Min', 80.0, today),  # Este es el mínimo
        ])
        price_tracker.conn.commit()

        result = price_tracker.get_books_with_historical_min_price()
        assert len(result) == 1
        assert result[0][0] == 'Book Min'
        assert result[0][1] == 80.0  # current price
        assert result[0][2] == 80.0  # min historical

    def test_current_not_historical_min(self, price_tracker):
        """No incluye libros que no están en mínimo histórico"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', [
            ('Book Not Min', 50.0, yesterday),  # Mínimo histórico
            ('Book Not Min', 80.0, today),  # Precio actual más alto
        ])
        price_tracker.conn.commit()

        result = price_tracker.get_books_with_historical_min_price()
        assert result == []

    def test_multiple_books_at_min(self, price_tracker):
        """Detecta múltiples libros en mínimo histórico"""
        today = date.today()

        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', [
            ('Book A', 50.0, today),
            ('Book B', 30.0, today),
        ])
        price_tracker.conn.commit()

        result = price_tracker.get_books_with_historical_min_price()
        assert len(result) == 2
        titles = [r[0] for r in result]
        assert 'Book A' in titles
        assert 'Book B' in titles

    def test_result_contains_date_record(self, price_tracker):
        """El resultado incluye la fecha del registro mínimo"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', [
            ('Book Date', 100.0, yesterday),
            ('Book Date', 80.0, today),
        ])
        price_tracker.conn.commit()

        result = price_tracker.get_books_with_historical_min_price()
        assert len(result) == 1
        # El cuarto elemento es la fecha del mínimo histórico
        assert result[0][3] == str(today)


class TestDemoData:
    """Pruebas para el método _get_demo_data"""

    def test_demo_data_returns_dict(self, price_tracker):
        """_get_demo_data retorna un diccionario"""
        result = price_tracker._get_demo_data()
        assert isinstance(result, dict)

    def test_demo_data_contains_products(self, price_tracker):
        """Los datos demo contienen objetos Product"""
        result = price_tracker._get_demo_data()
        for key, value in result.items():
            assert isinstance(value, Product)
            assert key == value.title

    def test_demo_data_has_expected_books(self, price_tracker):
        """Los datos demo contienen los libros esperados"""
        result = price_tracker._get_demo_data()
        expected_titles = [
            "Don Quijote de la Mancha",
            "Cien años de soledad",
            "Rayuela",
            "Pedro Páramo",
            "La casa de los espíritus"
        ]
        for title in expected_titles:
            assert title in result

    def test_demo_data_persists_to_db(self, price_tracker):
        """Los datos demo se guardan en la base de datos"""
        price_tracker._get_demo_data()

        price_tracker.cursor.execute("SELECT COUNT(*) FROM book_prices")
        count = price_tracker.cursor.fetchone()[0]
        assert count >= 5  # Al menos 5 libros demo


class TestGetWithMockedRequests:
    """Pruebas para get_data con requests mockeados"""

    def test_successful_scraping(self, price_tracker):
        """Obtiene datos correctamente cuando el scraping funciona"""
        mock_html = '''
        <html>
            <div class="listadoProductos">
                <div class="contenedorProducto producto">
                    <div class="titulo">Libro Test 1</div>
                    <div class="precioAhora">$1.234,56</div>
                </div>
                <div class="contenedorProducto producto">
                    <div class="titulo">Libro Test 2</div>
                    <div class="precioAhora">$2.345,67</div>
                </div>
            </div>
        </html>
        '''

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.text = mock_html

        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            result = price_tracker.get_data()

            assert isinstance(result, dict)
            assert len(result) == 2
            assert "Libro Test 1" in result
            assert result["Libro Test 1"].price == 1234.56

    def test_scraping_falls_back_to_demo(self, price_tracker):
        """Cuando falla el scraping, usa datos demo"""
        with patch('requests.Session') as mock_session_class:
            mock_session_class.side_effect = Exception("Network error")

            result = price_tracker.get_data()

            assert isinstance(result, dict)
            assert len(result) == 5  # 5 libros demo

    def test_non_200_status_falls_back(self, price_tracker):
        """Cuando el status no es 200/202, retorna string de error (no demo)"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.reason = "Server Error"
        mock_response.text = ""

        with patch('requests.Session') as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            mock_session_class.return_value = mock_session

            result = price_tracker.get_data()
            # El código actual retorna un string de error, no demo data
            # Esto es comportamiento esperado según la implementación
            assert isinstance(result, str)
            assert "Error" in result
            assert "500" in result


class TestShowMethods:
    """Pruebas para los métodos de visualización"""

    def test_show_price_decreases_with_data(self, price_tracker_with_data, capsys):
        """show_price_decreases muestra datos correctamente"""
        tracker = price_tracker_with_data
        tracker.compare_prices()
        tracker.show_price_decreases()

        captured = capsys.readouterr()
        assert "Libro A" in captured.out
        assert "disminuido" in captured.out.lower() or "Libro A" in captured.out

    def test_show_price_decreases_no_data(self, price_tracker, capsys):
        """show_price_decreases muestra mensaje cuando no hay datos"""
        tracker = price_tracker
        tracker.show_price_decreases()

        captured = capsys.readouterr()
        assert "No hay libros" in captured.out or "disminuido" in captured.out.lower()

    def test_show_changes_window_with_historical_min(self, price_tracker, capsys):
        """show_changes_window muestra libros en mínimo histórico"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', [
            ('Book Min', 100.0, yesterday),
            ('Book Min', 80.0, today),
        ])
        price_tracker.conn.commit()

        price_tracker.show_changes_window()

        captured = capsys.readouterr()
        assert "mínimo histórico" in captured.out.lower() or "Book Min" in captured.out

    def test_show_changes_window_no_data(self, price_tracker, capsys):
        """show_changes_window muestra mensaje cuando no hay datos"""
        price_tracker.show_changes_window()

        captured = capsys.readouterr()
        assert "No se encontraron" in captured.out or "mínimo histórico" in captured.out.lower()


class TestRun:
    """Pruebas para el método run"""

    def test_run_executes_full_flow(self, price_tracker_with_data):
        """run ejecuta el flujo completo"""
        # Mock get_data para retornar current_data
        with patch.object(price_tracker_with_data, 'get_data',
                         return_value=price_tracker_with_data.current_data):
            price_tracker_with_data.run()

        # Verificar que se compararon precios
        assert len(price_tracker_with_data.changes) > 0

    def test_run_handles_error_result(self, price_tracker, capsys):
        """run maneja correctamente un resultado de error"""
        with patch.object(price_tracker, 'get_data', return_value="Error: 500"):
            price_tracker.run()

        captured = capsys.readouterr()
        assert "Error" in captured.out or "500" in captured.out

    def test_run_no_changes_message(self, price_tracker, capsys):
        """run muestra mensaje cuando no hay cambios"""
        # Setup con datos iguales a ayer
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.executemany('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', [
            ('Book Same', 50.0, yesterday),
        ])
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Book Same': Product(title='Book Same', price=50.0)
        }

        with patch.object(price_tracker, 'get_data',
                         return_value=price_tracker.current_data):
            price_tracker.run()

        captured = capsys.readouterr()
        # Debe mostrar "no hubo cambios" o similar
        assert "No hubo cambios" in captured.out or "No hay libros" in captured.out


class TestEdgeCases:
    """Pruebas para casos borde"""

    def test_empty_current_data(self, price_tracker):
        """Maneja correctamente current_data vacío"""
        price_tracker.current_data = {}
        changes = price_tracker.compare_prices()
        assert changes == []
        assert price_tracker.price_decreases == []

    def test_yesterday_has_no_data(self, price_tracker):
        """Maneja cuando no hay datos de ayer"""
        today = date.today()

        price_tracker.current_data = {
            'New Book': Product(title='New Book', price=50.0)
        }

        # No insertar datos de ayer
        price_tracker.conn.commit()

        changes = price_tracker.compare_prices()
        # Debe ser detectado como nuevo producto
        assert len(changes) == 1
        assert changes[0][1] == "Nuevo producto"

    def test_price_zero_handling(self, price_tracker):
        """Maneja correctamente precio cero"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        price_tracker.cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', ('Free Book', 10.0, yesterday))
        price_tracker.conn.commit()

        price_tracker.current_data = {
            'Free Book': Product(title='Free Book', price=0.0)
        }

        changes = price_tracker.compare_prices()
        assert len(changes) == 1
        assert changes[0][1] == "Bajó"
        assert changes[0][2] == 10.0

    def test_database_unique_constraint(self, price_tracker):
        """La restricción UNIQUE funciona correctamente"""
        today = date.today()

        # Insertar mismo libro dos veces el mismo día
        price_tracker.cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', ('Duplicate Book', 50.0, today))

        price_tracker.cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)
        ''', ('Duplicate Book', 60.0, today))

        price_tracker.conn.commit()

        # Debe haber solo un registro
        price_tracker.cursor.execute(
            "SELECT COUNT(*) FROM book_prices WHERE title = 'Duplicate Book'"
        )
        count = price_tracker.cursor.fetchone()[0]
        assert count == 1
        # Debe tener el último precio
        price_tracker.cursor.execute(
            "SELECT price FROM book_prices WHERE title = 'Duplicate Book'"
        )
        price = price_tracker.cursor.fetchone()[0]
        assert price == 60.0
