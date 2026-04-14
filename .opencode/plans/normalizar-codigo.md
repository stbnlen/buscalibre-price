# Plan de Normalización del Código

## Diagnóstico

| # | Problema | Detalle |
|---|---------|---------|
| 1 | Tests duplicados | `tests/test_price_tracker.py` Y `tests/tracker/test_price_tracker.py` (este usa DB real) |
| 2 | Estructura de tests no refleja la fuente | `tracker/models.py` no tiene `test_models.py` separado |
| 3 | Tests mezclados | `test_price_tracker.py` contiene tests de `Product` (models.py) y `PriceTracker` juntos |
| 4 | Scripts sueltos duplican lógica | `check_price_decreases.py` y `create_test_data.py` reimplementan SQL y lógica existente en `tracker/` |
| 5 | SQL duplicado 6 veces | CREATE TABLE en: `price_tracker.py`, `check_price_decreases.py`, `create_test_data.py`, `conftest.py`, 2x en `test_create_test_data.py` |
| 6 | Fixtures redundantes | `test_create_test_data.py` define fixtures propios de DB en vez de usar `conftest.py` |
| 7 | Convenciones inconsistentes | Mezcla español/inglés, clases vs funciones sueltas, estilos de fixture distintos |

---

## Fase 1: Mover scripts al paquete `tracker/` y centralizar SQL

### 1.1 Crear `tracker/schema.py`

Nuevo archivo con las sentencias SQL centralizadas:

```python
"""Esquema centralizado de la base de datos."""

BOOK_PRICES_TABLE = '''
    CREATE TABLE IF NOT EXISTS book_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        price REAL NOT NULL,
        date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(title, date)
    )
'''

PRICE_CHANGES_TABLE = '''
    CREATE TABLE IF NOT EXISTS price_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        change_type TEXT NOT NULL,
        difference REAL NOT NULL,
        new_price REAL NOT NULL,
        date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
'''

INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_book_prices_date ON book_prices(date)',
    'CREATE INDEX IF NOT EXISTS idx_book_prices_title_date ON book_prices(title, date)',
    'CREATE INDEX IF NOT EXISTS idx_price_changes_date ON price_changes(date)',
]


def init_database(cursor) -> None:
    """Inicializa las tablas e índices en la base de datos."""
    cursor.execute(BOOK_PRICES_TABLE)
    cursor.execute(PRICE_CHANGES_TABLE)
    for index_sql in INDEXES:
        cursor.execute(index_sql)
```

### 1.2 Refactorizar `tracker/price_tracker.py`

- Reemplazar el método `_init_db` para usar `schema.init_database(self.cursor)` en vez de SQL inline
- Importar `from tracker import schema` o `from tracker.schema import init_database`

### 1.3 Mover `create_test_data.py` → `tracker/create_test_data.py`

- Mover el archivo
- Refactorizar para usar `PriceTracker` y `schema` en vez de SQL directo
- Mantener la funcionalidad de script standalone con `if __name__ == "__main__"`
- Usar `schema.init_database(cursor)` para crear tablas
- O mejor aún: usar `PriceTracker(db_path=...)` para obtener una conexión con el esquema ya inicializado

Estructura resultante:
```python
"""Script de utilidad para crear datos de prueba."""

import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

from tracker.schema import init_database

logger = logging.getLogger(__name__)

DB_PATH: Path = Path("buscalibre_prices.sqlite")


def create_test_data(db_path: Path | None = None) -> None:
    """Crea datos de prueba para ayer basado en los precios de hoy."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    try:
        init_database(cursor)  # Usar schema centralizado
        conn.commit()
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        cursor.execute(
            'SELECT title, price FROM book_prices WHERE date = ? LIMIT 5',
            (today,),
        )
        today_books = cursor.fetchall()

        if not today_books:
            logger.info("No hay datos de hoy para crear datos de prueba.")
            return

        for title, price in today_books:
            variation = random.uniform(-0.1, 0.1)
            yesterday_price = price * (1 + variation)

            cursor.execute(
                'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
                (title, yesterday_price, yesterday),
            )

        conn.commit()
    except sqlite3.Error as e:
        logger.error("Error de base de datos: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    create_test_data()
```

### 1.4 Mover `check_price_decreases.py` → `tracker/check_price_decreases.py`

- Mover el archivo
- Refactorizar para usar `PriceTracker` y `schema` en vez de reimplementar la lógica
- Usar `schema.init_database(cursor)` para crear tablas
- Idealmente usar `PriceTracker` para obtener los datos de precios en vez de SQL manual

Estructura resultante:
```python
"""Script de utilidad para verificar disminuciones de precio en la DB de producción."""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from tracker.schema import init_database

logger = logging.getLogger(__name__)

DB_PATH: Path = Path("buscalibre_prices.sqlite")


def check_price_decreases(db_path: Path | None = None) -> None:
    """Verifica disminuciones de precio en la base de datos de producción."""
    path = db_path or DB_PATH
    if not path.exists():
        logger.warning("Base de datos no encontrada en %s", path)
        return

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    try:
        init_database(cursor)  # Asegurar que las tablas existen
        conn.commit()

        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        cursor.execute('SELECT title, price FROM book_prices WHERE date = ?', (today,))
        today_data = dict(cursor.fetchall())

        cursor.execute('SELECT title, price FROM book_prices WHERE date = ?', (yesterday,))
        yesterday_data = dict(cursor.fetchall())

        cursor.execute('SELECT title, MIN(price) FROM book_prices GROUP BY title')
        historical_mins = dict(cursor.fetchall())

        decreases = []
        for title, current_price in today_data.items():
            if title in yesterday_data:
                old_price = yesterday_data[title]
                historical_min = historical_mins.get(title, 0)
                if current_price < old_price:
                    decreases.append((title, current_price, old_price, historical_min))

        if decreases:
            print("\n" + "=" * 90)
            print("LIBROS CON PRECIO DISMINUIDO RESPECTO AL DÍA ANTERIOR:")
            print("=" * 90)
            for title, current_price, previous_price, historical_min in decreases[:10]:
                print(f"Título: {title}")
                print(f"  Precio actual: ${current_price:,.2f}")
                print(f"  Precio del día anterior: ${previous_price:,.2f}")
                print(f"  Precio mínimo histórico: ${historical_min:,.2f}")
                print()
        else:
            print("No se encontraron libros con precio disminuido respecto al día anterior.")

    except sqlite3.Error as e:
        logger.error("Error de base de datos: %s", e)
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    check_price_decreases()
```

### 1.5 Actualizar `tracker/__init__.py`

Agregar las nuevas exportaciones:

```python
"""Price tracker package for monitoring book prices on Buscalibre."""

from tracker.models import Product
from tracker.price_tracker import PriceTracker

__all__ = ["PriceTracker", "Product"]
```

(Mantener igual, no es necesario exportar los scripts de utilidad)

### 1.6 Eliminar archivos raíz originales

- Eliminar `/create_test_data.py`
- Eliminar `/check_price_decreases.py`

---

## Fase 2: Normalizar estructura de tests

### 2.1 Eliminar `tests/tracker/` completo

Contiene tests obsoletos y de baja calidad:
- `tests/tracker/test_price_tracker.py` - se conecta a la DB real
- `tests/tracker/test_price_decrease_logic.py` - copia la lógica inline en vez de testear la API
- `tests/tracker/__init__.py` - vacío

### 2.2 Crear `tests/test_models.py`

Separar los tests de `Product` que están en `test_price_tracker.py`:

```python
"""Pruebas para los modelos de datos del tracker."""

import pytest
import logging

from tracker.models import Product


class TestProductCreation:
    """Pruebas para la creación de productos."""

    def test_creacion_correcta(self):
        """Se puede crear un producto correctamente."""
        product = Product(title="Test Book", price=100.0)
        assert product.title == "Test Book"
        assert product.price == 100.0

    def test_titulo_vacio_lanza_error(self):
        """Lanza ValueError si el título está vacío."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Product(title="", price=100.0)

    def test_titulo_solo_espacios_lanza_error(self):
        """Lanza ValueError si el título solo tiene espacios."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Product(title="   ", price=100.0)

    def test_precio_negativo_lanza_error(self):
        """Lanza ValueError si el precio es negativo."""
        with pytest.raises(ValueError, match="negative"):
            Product(title="Book", price=-10.0)

    def test_precio_cero_genera_warning(self, caplog):
        """Genera un warning si el precio es cero."""
        with caplog.at_level(logging.WARNING):
            Product(title="Free Book", price=0.0)
        assert "price of zero" in caplog.text


class TestProductEquality:
    """Pruebas para la igualdad y hashing de productos."""

    def test_igualdad_mismos_datos(self):
        """Dos productos con mismos datos son iguales."""
        p1 = Product(title="Book", price=50.0)
        p2 = Product(title="Book", price=50.0)
        assert p1 == p2

    def test_desigualdad_distinto_titulo(self):
        """Productos con distinto título no son iguales."""
        p1 = Product(title="Book A", price=50.0)
        p2 = Product(title="Book B", price=50.0)
        assert p1 != p2

    def test_desigualdad_distinto_precio(self):
        """Productos con distinto precio no son iguales."""
        p1 = Product(title="Book", price=50.0)
        p2 = Product(title="Book", price=60.0)
        assert p1 != p2

    def test_desigualdad_con_otro_tipo(self):
        """Producto no es igual a un objeto de otro tipo."""
        p = Product(title="Book", price=50.0)
        assert p != "Book"

    def test_hash_consistente(self):
        """El hash es consistente con la igualdad."""
        p1 = Product(title="Book", price=50.0)
        p2 = Product(title="Book", price=50.0)
        assert hash(p1) == hash(p2)

    def test_usable_en_conjunto(self):
        """Los productos se pueden usar en conjuntos."""
        p1 = Product(title="Book", price=50.0)
        p2 = Product(title="Book", price=50.0)
        p3 = Product(title="Other", price=30.0)
        s = {p1, p2, p3}
        assert len(s) == 2
```

### 2.3 Limpiar `tests/test_price_tracker.py`

Eliminar la clase `TestProduct` (ya movida a `test_models.py`) y mantener solo las clases de `PriceTracker`.

### 2.4 Crear `tests/test_check_price_decreases.py`

Tests para `tracker/check_price_decreases.py`:

```python
"""Pruebas para el script de verificación de disminuciones de precio."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from tracker.check_price_decreases import check_price_decreases


class TestCheckPriceDecreases:
    """Pruebas para la función check_price_decreases."""

    def test_base_datos_no_existente(self, caplog, tmp_path):
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
```

---

## Fase 3: Consolidar fixtures y SQL

### 3.1 Actualizar `tests/conftest.py`

Reemplazar SQL inline con `schema.init_database`:

```python
"""Configuración y fixtures para los tests de pytest."""

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
    """Crea una ruta temporal de base de datos sin inicializar tablas."""
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
    init_database(cursor)  # Usar schema centralizado
    conn.commit()
    conn.close()
    yield temp_db_path


@pytest.fixture
def db_connection(temp_db):
    """Provee una conexión a la base de datos para tests."""
    conn = sqlite3.connect(temp_db)
    yield conn
    conn.close()


@pytest.fixture
def price_tracker(temp_db, monkeypatch):
    """Crea un PriceTracker con base de datos temporal."""
    tracker = PriceTracker(db_path=temp_db)
    yield tracker
    tracker.close()


@pytest.fixture
def price_tracker_with_data(price_tracker):
    """Crea un PriceTracker con datos de prueba precargados."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    price_tracker.cursor.executemany(
        'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
        [
            ('Libro A', 22.00, two_days_ago),
            ('Libro B', 14.00, two_days_ago),
            ('Libro C', 28.00, two_days_ago),
        ],
    )

    price_tracker.cursor.executemany(
        'INSERT OR REPLACE INTO book_prices (title, price, date) VALUES (?, ?, ?)',
        [
            ('Libro A', 25.00, yesterday),
            ('Libro B', 15.50, yesterday),
            ('Libro C', 30.00, yesterday),
        ],
    )

    price_tracker.current_data = {
        'Libro A': Product(title='Libro A', price=20.00),
        'Libro B': Product(title='Libro B', price=15.50),
        'Libro C': Product(title='Libro C', price=35.00),
        'Libro D': Product(title='Libro D', price=12.00),
    }

    price_tracker.conn.commit()
    return price_tracker


@pytest.fixture
def sample_price_data():
    """Datos de precio de muestra para tests que no necesitan base de datos."""
    return {
        'today': {
            'Libro A': 20.00,
            'Libro B': 15.50,
            'Libro C': 35.00,
            'Libro D': 12.00,
        },
        'yesterday': {
            'Libro A': 25.00,
            'Libro B': 15.50,
            'Libro C': 30.00,
        },
        'historical_mins': {
            'Libro A': 18.00,
            'Libro B': 14.00,
            'Libro C': 28.00,
            'Libro D': 12.00,
        },
    }


@pytest.fixture
def sample_products():
    """Productos de muestra para tests."""
    return {
        'Libro A': Product(title='Libro A', price=20.00),
        'Libro B': Product(title='Libro B', price=15.50),
        'Libro C': Product(title='Libro C', price=35.00),
        'Libro D': Product(title='Libro D', price=12.00),
    }
```

### 3.2 Limpiar `tests/test_create_test_data.py`

- Eliminar fixture `create_test_data_module` (cargar con import normal ahora que está en el paquete)
- Eliminar fixtures `db_with_today_data` y `empty_db` (usar `temp_db` de conftest)
- Eliminar creación manual de tablas (usar `temp_db` que ya las tiene via `init_database`)
- Importar directamente: `from tracker.create_test_data import create_test_data`
- Usar parámetro `db_path` en vez de mockear `DB_PATH`

```python
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
        cursor.execute("SELECT price FROM book_prices WHERE date = ? AND title = ?", (yesterday, 'Libro X'))
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
            [('Libro 1', 100.0, today), ('Libro 2', 200.0, today), ('Libro 3', 300.0, today)],
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
```

---

## Fase 4: Unificar convenciones

### 4.1 Lenguaje consistente
- Todos los docstrings de tests en español (coherente con el proyecto)
- Nombres de métodos de test en español o descriptivos

### 4.2 Clases para organizar tests
- Todos los tests organizados en clases `Test*`
- Ya es mayoritariamente así, solo hay que aplicar a `tests/tracker/test_price_decrease_logic.py` y los nuevos tests

### 4.3 Verificar `tracker/price_tracker.py`
- Actualizar `_init_db` para usar `schema.init_database`
- Eliminar SQL inline

---

## Orden de ejecución

1. Crear `tracker/schema.py`
2. Refactorizar `tracker/price_tracker.py` (usar `schema.init_database`)
3. Mover y refactorizar `create_test_data.py` → `tracker/create_test_data.py`
4. Mover y refactorizar `check_price_decreases.py` → `tracker/check_price_decreases.py`
5. Eliminar archivos raíz originales
6. Actualizar `tracker/__init__.py`
7. Eliminar `tests/tracker/`
8. Crear `tests/test_models.py`
9. Limpiar `tests/test_price_tracker.py` (remover TestProduct)
10. Crear `tests/test_check_price_decreases.py`
11. Actualizar `tests/conftest.py` (usar `schema.init_database`)
12. Limpiar `tests/test_create_test_data.py` (usar imports directos y fixtures compartidos)
13. Actualizar `tests/test_price_decreases_logic.py` (convenciones)
14. Ejecutar `pytest` para verificar que todo funciona

## Estructura final del proyecto

```
buscalibre-price/
├── main.py                         # Entry point
├── pytest.ini
├── requirements.txt
├── tracker/
│   ├── __init__.py
│   ├── models.py                   # Product dataclass
│   ├── price_tracker.py            # PriceTracker (usa schema)
│   ├── schema.py                   # SQL centralizado
│   ├── check_price_decreases.py    # Utility (usa schema)
│   └── create_test_data.py         # Utility (usa schema)
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Fixtures (usa schema)
    ├── test_models.py              # Tests de Product
    ├── test_price_tracker.py       # Tests de PriceTracker
    ├── test_price_decreases_logic.py
    ├── test_create_test_data.py    # Tests con imports directos
    └── test_check_price_decreases.py  # Tests nuevos
```
