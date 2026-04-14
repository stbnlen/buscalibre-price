"""Esquema centralizado de la base de datos para la aplicación de seguimiento de precios.

Este módulo contiene las sentencias SQL para la creación de tablas e índices,
evitando la duplicación del esquema a lo largo del código.
"""

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
    """Inicializa las tablas e índices en la base de datos.

    Args:
        cursor: Un cursor de sqlite3 conectado a la base de datos.
    """
    cursor.execute(BOOK_PRICES_TABLE)
    cursor.execute(PRICE_CHANGES_TABLE)
    for index_sql in INDEXES:
        cursor.execute(index_sql)
