"""Domain exceptions for the price tracker application."""

from __future__ import annotations


class PriceTrackerError(Exception):
    """Base exception for all price tracker errors."""


class ConfigurationError(PriceTrackerError):
    """Raised when the application configuration is invalid."""


class ScrapingError(PriceTrackerError):
    """Raised when data scraping fails."""


class NetworkError(ScrapingError):
    """Raised when a network request fails after retries."""


class ParseError(ScrapingError):
    """Raised when the HTML response cannot be parsed as expected."""


class DatabaseError(PriceTrackerError):
    """Raised when a database operation fails."""
