"""Price tracker package for monitoring book prices on Buscalibre.

This package provides tools to scrape, store, and analyze book prices
from the Buscalibre website.
"""

from tracker.models import Product
from tracker.price_tracker import PriceTracker
from tracker.schema import init_database

__all__ = ["PriceTracker", "Product", "init_database"]
