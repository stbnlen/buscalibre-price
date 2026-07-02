"""Price analysis logic.

This module contains pure functions to compare prices, detect decreases,
and enrich historical minimum data. It does not perform I/O.
"""

from __future__ import annotations

from tracker.models import PriceChange, PriceDecrease, Product


CHANGE_NEW = "Nuevo producto"
CHANGE_UP = "Subió"
CHANGE_DOWN = "Bajó"


def compare_prices(
    current_data: dict[str, Product],
    last_prices: dict[str, float],
    historical_mins: dict[str, float],
) -> tuple[list[PriceChange], list[PriceDecrease]]:
    """Compare current prices against the previous recorded prices.

    Args:
        current_data: Products scraped today keyed by title.
        last_prices: Most recent price before today keyed by title.
        historical_mins: All-time minimum price per title.

    Returns:
        Tuple of (price changes, price decreases).
    """
    changes: list[PriceChange] = []
    decreases: list[PriceDecrease] = []

    for title, product in current_data.items():
        old_price = last_prices.get(title)
        historical_min = historical_mins.get(title)

        if old_price is None:
            changes.append(
                (title, CHANGE_NEW, product.price, product.price)
            )
        elif product.price > old_price:
            changes.append(
                (title, CHANGE_UP, product.price - old_price, product.price)
            )
        elif product.price < old_price:
            changes.append(
                (title, CHANGE_DOWN, old_price - product.price, product.price)
            )
            if historical_min is not None:
                decreases.append(
                    (title, product.price, old_price, historical_min)
                )

    return changes, decreases


def detect_decreases_between_dates(
    today_prices: dict[str, float],
    previous_prices: dict[str, float],
    historical_mins: dict[str, float],
) -> list[PriceDecrease]:
    """Detect price decreases between two arbitrary date snapshots.

    Args:
        today_prices: Prices for the current/most recent date.
        previous_prices: Prices for the comparison date.
        historical_mins: All-time minimum price per title.

    Returns:
        List of price decreases.
    """
    decreases: list[PriceDecrease] = []
    for title, current_price in today_prices.items():
        old_price = previous_prices.get(title)
        if old_price is None:
            continue
        if current_price < old_price:
            decreases.append(
                (title, current_price, old_price, historical_mins.get(title, 0))
            )
    return decreases
