"""Scraper module for extracting book prices from Buscalibre."""

from __future__ import annotations

import logging
from typing import Final

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tracker.config import (
    CURRENCY_SYMBOL,
    DECIMAL_SEPARATOR,
    HTTP_HEADERS,
    THOUSANDS_SEPARATOR,
)
from tracker.exceptions import NetworkError, ParseError
from tracker.models import Product

logger = logging.getLogger(__name__)

ACCEPTABLE_STATUS_CODES: Final[set[int]] = {200}


def _create_session(retries: int = 3) -> requests.Session:
    """Create a requests session with retry support."""
    session = requests.Session()
    session.headers.update(HTTP_HEADERS)

    retry_strategy = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist={429, 500, 502, 503, 504},
        allowed_methods={"HEAD", "GET", "OPTIONS"},
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _parse_price(raw_text: str) -> float | None:
    """Parse a Chilean-formatted price string into a float.

    Examples:
        "$12.345,67" -> 12345.67
        "$1.234" -> 1234.0
    """
    try:
        cleaned = (
            raw_text
            .replace(CURRENCY_SYMBOL, "")
            .replace(THOUSANDS_SEPARATOR, "")
            .replace(DECIMAL_SEPARATOR, ".")
            .strip()
        )
        price = float(cleaned)
    except ValueError:
        logger.warning("Could not parse price from: %r", raw_text)
        return None

    if price < 0:
        logger.warning("Negative price detected: %s", price)
        return None
    return price


class BuscalibreScraper:
    """Scraper for Buscalibre book list pages."""

    def __init__(self, url: str, timeout: int = 15, retries: int = 3) -> None:
        self.url = url
        self.timeout = timeout
        self.retries = retries

    def fetch(self) -> dict[str, Product]:
        """Fetch and parse products from the configured URL.

        Returns:
            Mapping of title to ``Product``.

        Raises:
            NetworkError: If the HTTP request fails after retries.
            ParseError: If the expected HTML structure is not found.
        """
        try:
            session = _create_session(self.retries)
            response = session.get(self.url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise NetworkError(
                f"Failed to fetch {self.url}: {exc}"
            ) from exc

        logger.debug(
            "HTTP %s - %s (%d bytes)",
            response.status_code,
            response.reason,
            len(response.text),
        )

        if response.status_code not in ACCEPTABLE_STATUS_CODES:
            raise NetworkError(
                f"Unexpected HTTP status {response.status_code} - "
                f"{response.reason}"
            )

        return self._parse_html(response.text)

    def _parse_html(self, html: str) -> dict[str, Product]:
        """Parse the Buscalibre HTML page into products."""
        soup = BeautifulSoup(html, "html.parser")

        parent_div = soup.find("div", class_="listadoProductos")
        if not parent_div:
            parent_div = soup.find(
                "div", class_=lambda x: x and "listado" in x.lower()
            )
        if not parent_div:
            parent_div = soup.find(
                "div", id=lambda x: x and "producto" in x.lower()
            )

        if not parent_div:
            preview = html[:200]
            raise ParseError(
                f"Product container not found. Preview: {preview}..."
            )

        products: dict[str, Product] = {}
        for product_div in parent_div.find_all(
            "div", class_="contenedorProducto producto"
        ):
            titulo = product_div.find("div", class_="titulo")
            precio = product_div.find("div", class_="precioAhora")

            if not titulo or not precio:
                continue

            title_text = titulo.get_text(strip=True)
            price_value = _parse_price(precio.get_text(strip=True))

            if price_value is None:
                logger.warning(
                    "Skipping product %r with invalid price", title_text
                )
                continue

            if title_text in products:
                logger.warning(
                    "Duplicate title %r found; keeping last occurrence",
                    title_text,
                )

            products[title_text] = Product(
                title=title_text, price=price_value
            )

        logger.info("Scraped %d products", len(products))
        return products
