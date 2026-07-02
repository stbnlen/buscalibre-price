"""Main entry point for the Buscalibre Price Tracker application.

This application monitors book prices from Buscalibre and tracks
price changes over time, alerting when prices reach historical minimums.

Configuration can be provided via environment variables:
    BUSCALIBRE_URL      URL to scrape
    BUSCALIBRE_DB_PATH  Path to the SQLite database
    BUSCALIBRE_TIMEOUT  HTTP request timeout in seconds
    BUSCALIBRE_RETRIES  Number of retries for failed HTTP requests

Or via command-line arguments (which override environment variables).

Usage:
    python main.py
    python main.py --url https://www.buscalibre.cl/v2/pendientes_1722693_l.html
    python main.py --db-path ./my_prices.sqlite --timeout 20 --retries 5
"""

from __future__ import annotations

import argparse
import logging
import sys

from tracker.config import DEFAULT_DB_PATH, DEFAULT_RETRIES, DEFAULT_TIMEOUT, DEFAULT_URL
from tracker.price_tracker import PriceTracker


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track and monitor Buscalibre book prices."
    )
    parser.add_argument(
        "--url",
        help="Buscalibre list URL to scrape",
    )
    parser.add_argument(
        "--db-path",
        help=f"Path to the SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help=f"HTTP request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        help=f"Number of HTTP retries (default: {DEFAULT_RETRIES})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the price tracker application."""
    args = _parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting Buscalibre Price Tracker")
    with PriceTracker(
        url=args.url,
        db_path=args.db_path,
        timeout=args.timeout,
        retries=args.retries,
    ) as tracker:
        tracker.run()
    logger.info("Price Tracker finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
