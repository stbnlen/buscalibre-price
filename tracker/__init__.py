"""Price tracker package for monitoring book prices on Buscalibre.

This package provides tools to scrape, store, and analyze book prices
from the Buscalibre website.
"""

from tracker.analyzer import compare_prices
from tracker.config import Config, load_config
from tracker.models import Product
from tracker.price_tracker import PriceTracker
from tracker.repository import PriceRepository
from tracker.schema import init_database
from tracker.scraper import BuscalibreScraper

__all__ = [
    "BuscalibreScraper",
    "Config",
    "PriceRepository",
    "PriceTracker",
    "Product",
    "compare_prices",
    "init_database",
    "load_config",
]
