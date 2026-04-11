"""Price tracker package for monitoring book prices on Buscalibre.

This package provides tools to scrape, store, and analyze book prices
from the Buscalibre website.
"""

from tracker.models import Product
from tracker.price_tracker import PriceTracker

__all__ = ["PriceTracker", "Product"]
