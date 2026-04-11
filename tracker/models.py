"""Data models for the price tracker application."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Product:
    """Represents a book product with its price.

    Attributes:
        title: The book title. Must not be empty.
        price: The book price in local currency. Must be non-negative.

    Raises:
        ValueError: If title is empty or price is negative.
    """

    title: str
    price: float

    def __post_init__(self) -> None:
        """Validate product data after initialization."""
        if not self.title or not self.title.strip():
            raise ValueError("Product title cannot be empty")

        if self.price < 0:
            raise ValueError(f"Price cannot be negative: {self.price}")

        if self.price == 0:
            logger.warning("Product '%s' has a price of zero", self.title)

    def __eq__(self, other: object) -> bool:
        """Check equality based on title and price."""
        if not isinstance(other, Product):
            return NotImplemented
        return self.title == other.title and self.price == other.price

    def __hash__(self) -> int:
        """Make Product hashable for use in sets/dicts."""
        return hash((self.title, self.price))
