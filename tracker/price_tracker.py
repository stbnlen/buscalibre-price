"""Price tracker module for monitoring book prices on Buscalibre.

This module provides functionality to scrape book prices from Buscalibre,
store them in a SQLite database, and analyze price changes over time.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

from tracker.models import Product

# Constants
DEFAULT_URL: str = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"
DEFAULT_DB_PATH: str = "buscalibre_prices.sqlite"
DEFAULT_TIMEOUT: int = 15
ACCEPTABLE_STATUS_CODES: set[int] = {200, 202}

# Scraping constants
CURRENCY_SYMBOL: str = "$"
THOUSANDS_SEPARATOR: str = "."
DECIMAL_SEPARATOR: str = ","

# HTTP headers
HTTP_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

logger = logging.getLogger(__name__)


@dataclass
class PriceTracker:
    """Tracks book prices from Buscalibre and analyzes changes.

    Attributes:
        url: The URL to scrape for price data.
        db_path: Path to the SQLite database file.
        timeout: HTTP request timeout in seconds.
        current_data: Dictionary of current product data.
        changes: List of price change tuples.
        price_decreases: List of price decrease tuples.
    """

    url: str = DEFAULT_URL
    db_path: str | Path = DEFAULT_DB_PATH
    timeout: int = DEFAULT_TIMEOUT
    current_data: dict[str, Product] = field(default_factory=dict)
    changes: list[tuple[str, str, float, float]] = field(default_factory=list)
    price_decreases: list[tuple[str, float, float, float]] = field(default_factory=list)

    # Internal attributes (not exposed in constructor)
    _conn: sqlite3.Connection | None = field(default=None, repr=False)
    _cursor: sqlite3.Cursor | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize database connection and create tables if needed."""
        # Convert db_path to Path if it's a string
        if isinstance(self.db_path, str):
            self.db_path = Path(self.db_path)

        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        """Get database connection, creating it if needed."""
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        return self._conn

    @property
    def cursor(self) -> sqlite3.Cursor:
        """Get database cursor, creating it if needed."""
        if self._cursor is None:
            raise RuntimeError("Database cursor not initialized")
        return self._cursor

    def _init_db(self) -> None:
        """Initialize the SQLite database and create tables if they don't exist."""
        try:
            self._conn = sqlite3.connect(self.db_path)
            self._cursor = self.conn.cursor()

            # Create table for daily prices
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS book_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    price REAL NOT NULL,
                    date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(title, date)
                )
            ''')

            # Create table for price changes
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    difference REAL NOT NULL,
                    new_price REAL NOT NULL,
                    date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            self.conn.commit()
            logger.debug("Database initialized at %s", self.db_path)
        except sqlite3.Error as e:
            logger.error("Failed to initialize database: %s", e)
            raise

    @contextmanager
    def database_transaction(self):
        """Context manager for database transactions.

        Yields:
            sqlite3.Cursor: Database cursor for the transaction.

        Raises:
            sqlite3.Error: If the transaction fails.
        """
        conn = self.conn
        try:
            yield self.cursor
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logger.error("Database transaction failed: %s", e)
            raise

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._cursor = None
            logger.debug("Database connection closed")

    def __enter__(self) -> PriceTracker:
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc_val: BaseException | None,
                 exc_tb: Any | None) -> None:
        """Exit context manager and close connection."""
        self.close()

    def __del__(self) -> None:
        """Destructor to ensure connection is closed."""
        self.close()

    def _parse_price(self, raw_text: str) -> float | None:
        """Parse a price string into a float.

        Args:
            raw_text: Raw price text from HTML (e.g., "$1.234,56").

        Returns:
            Parsed price as float, or None if parsing fails.
        """
        try:
            cleaned = (
                raw_text
                .replace(CURRENCY_SYMBOL, "")
                .replace(THOUSANDS_SEPARATOR, "")
                .replace(DECIMAL_SEPARATOR, ".")
            )
            price = float(cleaned)
            if price < 0:
                logger.warning("Negative price detected: %s", price)
                return None
            return price
        except ValueError:
            logger.warning("Could not parse price from: %r", raw_text)
            return None

    def _save_price(self, title: str, price: float, date: datetime | None = None) -> None:
        """Save a price record to the database.

        Args:
            title: Book title.
            price: Book price.
            date: Date for the price record (defaults to today).
        """
        if date is None:
            date = datetime.now().date()

        self.cursor.execute('''
            INSERT OR REPLACE INTO book_prices (title, price, date)
            VALUES (?, ?, ?)
        ''', (title, price, date))

    def _create_session(self) -> requests.Session:
        """Create and configure a requests session.

        Returns:
            Configured requests Session object.
        """
        session = requests.Session()
        session.headers.update(HTTP_HEADERS)
        return session

    def get_data(self) -> dict[str, Product] | str:
        """Fetch current price data from Buscalibre website.

        Attempts to scrape price data from the configured URL. If scraping
        fails, falls back to demo data.

        Returns:
            Dictionary of Product objects keyed by title, or error string.
        """
        try:
            session = self._create_session()
            response = session.get(self.url, timeout=self.timeout)

            logger.debug(
                "HTTP %s - %s (%d bytes)",
                response.status_code,
                response.reason,
                len(response.text)
            )

            # Save HTML for debugging
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.debug("HTML saved to debug.html")

            if response.status_code not in ACCEPTABLE_STATUS_CODES:
                error_msg = f"Error: {response.status_code} - {response.reason}"
                logger.error(error_msg)
                return error_msg

            soup = BeautifulSoup(response.text, "html.parser")
            parent_div = soup.find("div", class_="listadoProductos")

            if not parent_div:
                # Try alternative selectors
                parent_div = soup.find("div", class_=lambda x: x and "listado" in x.lower())
                if not parent_div:
                    parent_div = soup.find("div", id=lambda x: x and "producto" in x.lower())

                if not parent_div:
                    preview = response.text[:200]
                    error_msg = f"Div con clase 'listadoProductos' no encontrado. Preview: {preview}..."
                    logger.error(error_msg)
                    return error_msg

            # Parse products
            products: dict[str, Product] = {}
            for product_div in parent_div.find_all("div", class_="contenedorProducto producto"):
                titulo = product_div.find("div", class_="titulo")
                precio = product_div.find("div", class_="precioAhora")

                if not titulo or not precio:
                    continue

                title_text = titulo.get_text(strip=True)
                price_value = self._parse_price(precio.get_text(strip=True))

                if price_value is None:
                    logger.warning("Skipping product '%s' with invalid price", title_text)
                    continue

                products[title_text] = Product(title=title_text, price=price_value)

            # Save to database
            today = datetime.now().date()
            for product in products.values():
                self._save_price(product.title, product.price, today)
            self.conn.commit()

            logger.info("Scraped %d products", len(products))
            self.current_data = products
            return products

        except requests.RequestException as e:
            logger.error("Network error fetching data: %s", e)
        except sqlite3.Error as e:
            logger.error("Database error saving data: %s", e)
        except Exception as e:
            logger.error("Unexpected error fetching data: %s", e, exc_info=True)

        # Fallback to demo data
        return self._get_demo_data()

    def _get_demo_data(self) -> dict[str, Product]:
        """Provide demo data when scraping fails.

        Returns:
            Dictionary of demo Product objects keyed by title.
        """
        logger.info("Using demo data as fallback")
        demo_products = {
            "Don Quijote de la Mancha": Product("Don Quijote de la Mancha", 15000.0),
            "Cien años de soledad": Product("Cien años de soledad", 18000.0),
            "Rayuela": Product("Rayuela", 16500.0),
            "Pedro Páramo": Product("Pedro Páramo", 12000.0),
            "La casa de los espíritus": Product("La casa de los espíritus", 17500.0)
        }

        # Save demo data to database
        today = datetime.now().date()
        for product in demo_products.values():
            self._save_price(product.title, product.price, today)
        self.conn.commit()

        self.current_data = demo_products
        return demo_products

    def get_books_with_historical_min_price(self) -> list[tuple[str, float, float, str]]:
        """Get books whose current price equals their historical minimum.

        Returns:
            List of tuples (title, current_price, min_historical_price, date_record).
        """
        # Get the latest date in the database
        self.cursor.execute('SELECT MAX(date) FROM book_prices')
        latest_date = self.cursor.fetchone()[0]

        if not latest_date:
            return []

        # Single optimized query to get all data at once
        self.cursor.execute('''
            WITH latest_prices AS (
                SELECT title, price as current_price
                FROM book_prices
                WHERE date = ?
            ),
            historical_mins AS (
                SELECT title, MIN(price) as min_price
                FROM book_prices
                GROUP BY title
            ),
            min_dates AS (
                SELECT title, MIN(date) as first_min_date
                FROM book_prices
                WHERE (title, price) IN (
                    SELECT title, MIN(price) FROM book_prices GROUP BY title
                )
                GROUP BY title
            )
            SELECT lp.title, lp.current_price, hm.min_price, md.first_min_date
            FROM latest_prices lp
            JOIN historical_mins hm ON lp.title = hm.title
            JOIN min_dates md ON lp.title = md.title
            WHERE lp.current_price = hm.min_price
            ORDER BY lp.title
        ''', (latest_date,))

        results = self.cursor.fetchall()

        # Convert date objects to strings if needed
        return [
            (title, current_price, min_price, str(date_record))
            for title, current_price, min_price, date_record in results
        ]

    def compare_prices(self) -> list[tuple[str, str, float, float]]:
        """Compare current prices with yesterday's prices.

        Identifies price increases, decreases, and new products.

        Returns:
            List of tuples (title, change_type, difference, new_price).
        """
        yesterday = (datetime.now() - timedelta(days=1)).date()

        # Get yesterday's prices
        self.cursor.execute('''
            SELECT title, price FROM book_prices WHERE date = ?
        ''', (yesterday,))
        yesterday_data = dict(self.cursor.fetchall())

        # Get historical minimums
        self.cursor.execute('''
            SELECT title, MIN(price) FROM book_prices GROUP BY title
        ''')
        historical_mins = dict(self.cursor.fetchall())

        self.changes = []
        self.price_decreases = []

        for title, current_product in self.current_data.items():
            old_price = yesterday_data.get(title)
            historical_min = historical_mins.get(title)

            if old_price is None:
                # New product
                self.changes.append((
                    title,
                    "Nuevo producto",
                    current_product.price,
                    current_product.price
                ))
            elif current_product.price > old_price:
                # Price increased
                self.changes.append((
                    title,
                    "Subió",
                    current_product.price - old_price,
                    current_product.price
                ))
            elif current_product.price < old_price:
                # Price decreased
                self.changes.append((
                    title,
                    "Bajó",
                    old_price - current_product.price,
                    current_product.price
                ))
                # Track for price decrease visualization
                if historical_min is not None:
                    self.price_decreases.append((
                        title,
                        current_product.price,
                        old_price,
                        historical_min
                    ))
            # else: No change, skip

        # Save changes to database
        if self.changes:
            today = datetime.now().date()
            for title, status, diff, new_price in self.changes:
                self.cursor.execute('''
                    INSERT INTO price_changes (title, change_type, difference, new_price, date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (title, status, diff, new_price, today))
            self.conn.commit()

        logger.info(
            "Compared prices: %d changes, %d decreases",
            len(self.changes),
            len(self.price_decreases)
        )
        return self.changes

    def show_changes_window(self) -> None:
        """Display books at historical minimum price with comparison data."""
        min_price_books = self.get_books_with_historical_min_price()

        if not min_price_books:
            print("No se encontraron libros con precio actual igual al mínimo histórico.")
            return

        today = datetime.now().date()

        # Batch query for last prices before today
        titles = [book[0] for book in min_price_books]
        placeholders = ','.join('?' for _ in titles)
        self.cursor.execute(f'''
            SELECT bp1.title, bp1.price, bp1.date
            FROM book_prices bp1
            INNER JOIN (
                SELECT title, MAX(date) as max_date
                FROM book_prices
                WHERE date < ? AND title IN ({placeholders})
                GROUP BY title
            ) bp2 ON bp1.title = bp2.title AND bp1.date = bp2.max_date
        ''', [today] + titles)
        last_prices_map = {row[0]: (row[1], row[2]) for row in self.cursor.fetchall()}

        # Build enhanced data
        enhanced_data = []
        for title, current_price, min_price, date_record in min_price_books:
            last_price_info = last_prices_map.get(title)
            if last_price_info:
                last_price, last_price_date = last_price_info
            else:
                last_price, last_price_date = None, None

            # Calculate difference and percentage
            if last_price is not None:
                difference = current_price - last_price
                pct_change = (difference / last_price) * 100 if last_price != 0 else 0
            else:
                difference = None
                pct_change = None

            enhanced_data.append((
                title, current_price, last_price, last_price_date,
                difference, pct_change, min_price, date_record
            ))

        # Create and format DataFrame
        df = pd.DataFrame(enhanced_data,
                         columns=['Título', 'Precio Hoy', 'Último Precio Registrado',
                                  'Fecha Último Precio', 'Diferencia', '% Cambio',
                                  'Mínimo Histórico', 'Fecha Mínimo Histórico'])

        # Format currency columns
        df['Precio Hoy'] = df['Precio Hoy'].apply(lambda x: f"${x:,.2f}")
        df['Último Precio Registrado'] = df['Último Precio Registrado'].apply(
            lambda x: f"${x:,.2f}" if x is not None else "N/A"
        )
        df['Fecha Último Precio'] = df['Fecha Último Precio'].apply(
            lambda x: str(x) if x is not None else "N/A"
        )
        df['Diferencia'] = df['Diferencia'].apply(
            lambda x: f"{x:+,.2f}" if x is not None else "N/A"
        )
        df['% Cambio'] = df['% Cambio'].apply(
            lambda x: f"{x:+.2f}%" if x is not None else "N/A"
        )
        df['Mínimo Histórico'] = df['Mínimo Histórico'].apply(lambda x: f"${x:,.2f}")

        print("\nLibros con precio actual igual al mínimo histórico "
              "(comparación con último precio registrado):")
        print(df.to_string(index=False))

    def show_price_decreases(self) -> None:
        """Display books whose prices decreased compared to yesterday."""
        if not self.price_decreases:
            print("No hay libros con precio disminuido respecto al día anterior.")
            return

        df = pd.DataFrame(self.price_decreases,
                         columns=['Título', 'Precio Actual', 'Precio Día Anterior', 'Mínimo Histórico'])

        # Format currency columns
        df['Precio Actual'] = df['Precio Actual'].apply(lambda x: f"${x:,.2f}")
        df['Precio Día Anterior'] = df['Precio Día Anterior'].apply(lambda x: f"${x:,.2f}")
        df['Mínimo Histórico'] = df['Mínimo Histórico'].apply(lambda x: f"${x:,.2f}")

        print("\nLibros con precio disminuido respecto al día anterior:")
        print(df.to_string(index=False))

    def run(self) -> None:
        """Execute the full price tracking workflow.

        Fetches data, compares prices, and displays results.
        """
        result = self.get_data()

        if isinstance(result, dict):
            self.compare_prices()

            # Show price decreases
            if self.price_decreases:
                self.show_price_decreases()

            # Show changes window
            if self.changes:
                self.show_changes_window()
            elif not self.price_decreases:
                print("No hubo cambios en los precios.")
        else:
            # result is an error string
            print(result)
