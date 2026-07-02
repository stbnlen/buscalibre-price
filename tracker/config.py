"""Application configuration.

Configuration values are read from environment variables and can be
overridden via command-line arguments in ``main.py``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DEFAULT_URL: Final[str] = (
    "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"
)
DEFAULT_DB_PATH: Final[Path] = Path("buscalibre_prices.sqlite")
DEFAULT_TIMEOUT: Final[int] = 15
DEFAULT_RETRIES: Final[int] = 3

CURRENCY_SYMBOL: Final[str] = "$"
THOUSANDS_SEPARATOR: Final[str] = "."
DECIMAL_SEPARATOR: Final[str] = ","

HTTP_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


@dataclass(frozen=True, slots=True)
class Config:
    """Application configuration.

    Attributes:
        url: Buscalibre list URL to scrape.
        db_path: Path to the SQLite database file.
        timeout: HTTP request timeout in seconds.
        retries: Number of retries for failed HTTP requests.
    """

    url: str = DEFAULT_URL
    db_path: Path = DEFAULT_DB_PATH
    timeout: int = DEFAULT_TIMEOUT
    retries: int = DEFAULT_RETRIES


def load_config(
    url: str | None = None,
    db_path: str | Path | None = None,
    timeout: int | None = None,
    retries: int | None = None,
) -> Config:
    """Load configuration from environment variables and overrides.

    Environment variables:
        - BUSCALIBRE_URL
        - BUSCALIBRE_DB_PATH
        - BUSCALIBRE_TIMEOUT
        - BUSCALIBRE_RETRIES

    Explicit arguments take precedence over environment variables, which in
    turn take precedence over the built-in defaults.
    """
    env_url = os.environ.get("BUSCALIBRE_URL")
    env_db_path = os.environ.get("BUSCALIBRE_DB_PATH")
    env_timeout = os.environ.get("BUSCALIBRE_TIMEOUT")
    env_retries = os.environ.get("BUSCALIBRE_RETRIES")

    final_url = url or env_url or DEFAULT_URL
    final_db_path = Path(db_path) if db_path else (
        Path(env_db_path) if env_db_path else DEFAULT_DB_PATH
    )

    final_timeout = DEFAULT_TIMEOUT
    for value in (timeout, env_timeout):
        if value is not None:
            try:
                final_timeout = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid timeout value: {value!r}"
                ) from exc
            break

    final_retries = DEFAULT_RETRIES
    for value in (retries, env_retries):
        if value is not None:
            try:
                final_retries = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid retries value: {value!r}"
                ) from exc
            break

    return Config(
        url=final_url,
        db_path=final_db_path,
        timeout=final_timeout,
        retries=final_retries,
    )
