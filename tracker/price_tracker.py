"""Price tracker orchestrator.

This module exposes ``PriceTracker``, a high-level class that coordinates
scraping, persistence, analysis, and reporting. The actual work is delegated
to specialized modules so this class remains small and easy to test.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from tracker.analyzer import compare_prices
from tracker.config import Config, load_config
from tracker.exceptions import ScrapingError
from tracker.models import PriceChange, PriceDecrease, Product
from tracker.repository import PriceRepository
from tracker.reporter import (
    format_historical_min_books,
    format_price_decreases,
)
from tracker.scraper import BuscalibreScraper

logger = logging.getLogger(__name__)


@dataclass
class PriceTracker:
    """High-level orchestrator for the price tracking workflow.

    The class keeps the same public shape as the previous implementation
    (``get_data``, ``compare_prices``, ``run``, etc.) but delegates the work
    to smaller, focused components.
    """

    url: str | None = None
    db_path: str | Path | None = None
    timeout: int | None = None
    retries: int | None = None

    current_data: dict[str, Product] = field(default_factory=dict)
    changes: list[PriceChange] = field(default_factory=list)
    price_decreases: list[PriceDecrease] = field(default_factory=list)
    _cursor: sqlite3.Cursor | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.config: Config = load_config(
            url=self.url,
            db_path=self.db_path,
            timeout=self.timeout,
            retries=self.retries,
        )
        self.repository = PriceRepository(self.config.db_path)
        # Force connection (and schema creation) so that ``cursor`` is
        # available immediately after construction, matching the previous
        # behaviour expected by the test suite.
        self._cursor = self.repository.conn.cursor()
        self.scraper = BuscalibreScraper(
            url=self.config.url,
            timeout=self.config.timeout,
            retries=self.config.retries,
        )

    @property
    def conn(self):
        """Expose the repository connection for backwards compatibility."""
        return self.repository.conn

    @property
    def cursor(self) -> sqlite3.Cursor:
        """Expose the repository cursor for backwards compatibility."""
        if self._cursor is None:
            self._cursor = self.repository.conn.cursor()
        return self._cursor

    def close(self) -> None:
        """Close the database connection."""
        self._cursor = None
        self.repository.close()

    def __enter__(self) -> PriceTracker:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    def get_data(self, for_date: date | None = None) -> dict[str, Product]:
        """Scrape current prices and persist them.

        Args:
            for_date: Date to associate with the scraped prices. Defaults to
                the current local date.

        Returns:
            Mapping of title to ``Product`` on success.

        Raises:
            ScrapingError: If the scraper fails to fetch or parse the page.
        """
        products = self.scraper.fetch()

        if for_date is None:
            for_date = datetime.now().date()

        self.repository.save_prices(products, for_date)
        self.current_data = products
        return products

    def get_books_with_historical_min_price(
        self, for_date: date | None = None
    ) -> list[tuple[str, float, float, str]]:
        """Return books currently at their historical minimum price."""
        return self.repository.get_books_with_historical_min_price(for_date)

    def compare_prices(self, for_date: date | None = None) -> list[PriceChange]:
        """Compare current prices with the last recorded prices.

        Persist the resulting changes to the database.

        Args:
            for_date: Date to use as "today". Defaults to the current local
                date.
        """
        if for_date is None:
            for_date = datetime.now().date()

        last_prices = self.repository.get_last_prices_before(for_date)
        historical_mins = self.repository.get_historical_mins()

        self.changes, self.price_decreases = compare_prices(
            self.current_data, last_prices, historical_mins
        )

        self.repository.save_price_changes(self.changes, for_date)

        logger.info(
            "Compared prices: %d changes, %d decreases",
            len(self.changes),
            len(self.price_decreases),
        )
        return self.changes

    def show_changes_window(self, for_date: date | None = None) -> str:
        """Return a formatted report of books at their historical low."""
        min_price_books = self.get_books_with_historical_min_price(for_date)

        if not min_price_books:
            return (
                "No se encontraron libros con precio actual igual al "
                "mínimo histórico."
            )

        if for_date is None:
            for_date = datetime.now().date()

        last_prices_with_dates = (
            self.repository.get_last_prices_with_dates_before(for_date)
        )

        return format_historical_min_books(
            min_price_books, last_prices_with_dates
        )

    def show_price_decreases(self) -> str:
        """Return a formatted report of recent price decreases."""
        return format_price_decreases(self.price_decreases)

    def run(self) -> None:
        """Execute the full tracking workflow."""
        today = datetime.now().date()

        try:
            self.get_data(for_date=today)
        except ScrapingError as exc:
            logger.error("Failed to obtain Buscalibre data: %s", exc)
            print("Error: No se pudieron obtener los datos de Buscalibre.")
            return

        self.compare_prices(for_date=today)

        if self.price_decreases:
            print(self.show_price_decreases())

        if self.changes:
            print(self.show_changes_window(for_date=today))
        elif not self.price_decreases:
            print("No hubo cambios en los precios.")
