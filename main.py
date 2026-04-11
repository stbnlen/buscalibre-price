"""Main entry point for the Buscalibre Price Tracker application.

This application monitors book prices from Buscalibre and tracks
price changes over time, alerting when prices reach historical minimums.

Usage:
    python main.py
"""

import logging

from tracker.price_tracker import PriceTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the price tracker application."""
    logger.info("Starting Buscalibre Price Tracker")
    with PriceTracker() as tracker:
        tracker.run()
    logger.info("Price Tracker finished")


if __name__ == "__main__":
    main()
