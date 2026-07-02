"""Database repository for the price tracker application."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

from tracker.exceptions import DatabaseError
from tracker.models import HistoricalMinBook, PriceChange, Product
from tracker.schema import init_database

logger = logging.getLogger(__name__)

# Register explicit SQLite adapter for Python 3.12+ compatibility.
# The date values are read back as strings and converted explicitly where
# needed, so no converter is registered globally.
sqlite3.register_adapter(date, lambda d: d.isoformat())


class PriceRepository:
    """Repository for price and price-change persistence."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Open the database connection and initialize the schema."""
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(self.db_path)
                init_database(self._conn.cursor())
                self._conn.commit()
            except sqlite3.Error as exc:
                logger.error("Failed to initialize database: %s", exc)
                raise DatabaseError(
                    f"Failed to initialize database: {exc}"
                ) from exc
        return self._conn

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the active connection, opening it if necessary."""
        return self._connect()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.debug("Database connection closed")

    def __enter__(self) -> PriceRepository:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @contextmanager
    def transaction(self):
        """Context manager for a database transaction."""
        conn = self.conn
        try:
            yield conn.cursor()
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            logger.error("Database transaction failed: %s", exc)
            raise DatabaseError(
                f"Database transaction failed: {exc}"
            ) from exc

    def save_price(self, title: str, price: float, for_date: date) -> None:
        """Insert or replace a price record for a specific date."""
        with self.transaction() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO book_prices (title, price, date)
                VALUES (?, ?, ?)
                """,
                (title, price, for_date),
            )

    def save_prices(
        self, products: dict[str, Product], for_date: date
    ) -> None:
        """Insert or replace price records for many products."""
        with self.transaction() as cursor:
            cursor.executemany(
                """
                INSERT OR REPLACE INTO book_prices (title, price, date)
                VALUES (?, ?, ?)
                """,
                [
                    (product.title, product.price, for_date)
                    for product in products.values()
                ],
            )

    def get_prices_for_date(self, for_date: date) -> dict[str, float]:
        """Return title -> price for the requested date."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT title, price FROM book_prices WHERE date = ?",
            (for_date,),
        )
        return dict(cursor.fetchall())

    def get_last_prices_before(self, before_date: date) -> dict[str, float]:
        """Return the most recent price per title strictly before a date."""
        return {
            title: price
            for title, (price, _) in self.get_last_prices_with_dates_before(
                before_date
            ).items()
        }

    def get_last_prices_with_dates_before(
        self, before_date: date
    ) -> dict[str, tuple[float, date]]:
        """Return the most recent (price, date) per title before a date."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT bp1.title, bp1.price, bp1.date
            FROM book_prices bp1
            INNER JOIN (
                SELECT title, MAX(date) as max_date
                FROM book_prices
                WHERE date < ?
                GROUP BY title
            ) bp2 ON bp1.title = bp2.title AND bp1.date = bp2.max_date
            """,
            (before_date,),
        )
        return {
            title: (price, date.fromisoformat(date_str))
            for title, price, date_str in cursor.fetchall()
        }

    def get_historical_mins(self) -> dict[str, float]:
        """Return the minimum price ever recorded per title."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT title, MIN(price) FROM book_prices GROUP BY title"
        )
        return dict(cursor.fetchall())

    def get_books_with_historical_min_price(
        self, for_date: date | None = None
    ) -> list[HistoricalMinBook]:
        """Return books whose price on ``for_date`` equals their all-time low.

        If ``for_date`` is not provided, the latest date in the database is
        used.
        """
        cursor = self.conn.cursor()

        if for_date is None:
            cursor.execute("SELECT MAX(date) FROM book_prices")
            row = cursor.fetchone()
            latest_date = row[0] if row else None
            if not latest_date:
                return []
            for_date = date.fromisoformat(latest_date)

        cursor.execute(
            """
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
            """,
            (for_date,),
        )

        return [
            (title, current_price, min_price, str(date_record))
            for title, current_price, min_price, date_record in cursor.fetchall()
        ]

    def save_price_changes(
        self, changes: list[PriceChange], for_date: date
    ) -> None:
        """Persist a list of price changes."""
        if not changes:
            return

        with self.transaction() as cursor:
            cursor.executemany(
                """
                INSERT INTO price_changes
                    (title, change_type, difference, new_price, date)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (title, change_type, difference, new_price, for_date)
                    for title, change_type, difference, new_price in changes
                ],
            )

    def get_max_date(self) -> date | None:
        """Return the latest date stored in ``book_prices``."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(date) FROM book_prices")
        row = cursor.fetchone()
        if row and row[0]:
            return date.fromisoformat(row[0])
        return None
