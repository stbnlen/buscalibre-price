"""Reporting utilities that return formatted strings.

All functions return ``str`` instead of printing to ``stdout``. This makes
output easy to test, redirect, or send via email/notification.
"""

from __future__ import annotations

from tabulate import tabulate

from tracker.models import HistoricalMinBook, PriceDecrease


def _fmt_price(value: float | None) -> str:
    """Format a price in Chilean format."""
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def _fmt_diff(value: float | None) -> str:
    """Format a signed difference."""
    if value is None:
        return "N/A"
    return f"{value:+,.2f}"


def _fmt_pct(value: float | None) -> str:
    """Format a signed percentage."""
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


def format_price_decreases(decreases: list[PriceDecrease]) -> str:
    """Return a formatted table of price decreases."""
    if not decreases:
        return "No hay libros con precio disminuido respecto al registro anterior."

    rows = [
        (title, _fmt_price(current), _fmt_price(old), _fmt_price(hist_min))
        for title, current, old, hist_min in decreases
    ]

    return (
        "\nLibros con precio disminuido respecto al registro anterior:\n"
        + tabulate(
            rows,
            headers=[
                "Título",
                "Precio Actual",
                "Precio Registro Anterior",
                "Mínimo Histórico",
            ],
            tablefmt="simple",
        )
    )


def format_historical_min_books(
    books: list[HistoricalMinBook],
    last_prices: dict[str, tuple[float, date]] | None = None,
) -> str:
    """Return a formatted table of books currently at their historical low.

    Args:
        books: Output of ``PriceRepository.get_books_with_historical_min_price``.
        last_prices: Optional mapping of title -> (price, date) for the last
            recorded price before today.
    """
    if not books:
        return (
            "No se encontraron libros con precio actual igual al "
            "mínimo histórico."
        )

    last_prices = last_prices or {}
    rows: list[tuple[str, str, str, str, str, str, str, str]] = []

    for title, current_price, min_price, first_min_date in books:
        last_price_info = last_prices.get(title)
        if last_price_info:
            last_price, last_price_date = last_price_info
            difference = current_price - last_price
            pct_change = (
                (difference / last_price) * 100 if last_price != 0 else 0.0
            )
        else:
            last_price, last_price_date, difference, pct_change = (
                None,
                None,
                None,
                None,
            )

        rows.append(
            (
                title,
                _fmt_price(current_price),
                _fmt_price(last_price),
                str(last_price_date) if last_price_date is not None else "N/A",
                _fmt_diff(difference),
                _fmt_pct(pct_change),
                _fmt_price(min_price),
                first_min_date,
            )
        )

    return (
        "\nLibros con precio actual igual al mínimo histórico "
        "(comparación con último precio registrado):\n"
        + tabulate(
            rows,
            headers=[
                "Título",
                "Precio Hoy",
                "Último Precio Registrado",
                "Fecha Último Precio",
                "Diferencia",
                "% Cambio",
                "Mínimo Histórico",
                "Fecha Mínimo Histórico",
            ],
            tablefmt="simple",
        )
    )


def format_check_decreases(decreases: list[PriceDecrease]) -> str:
    """Return a plain-text report for the check_price_decreases script."""
    if not decreases:
        return (
            "No se encontraron libros con precio disminuido "
            "respecto al día anterior."
        )

    lines: list[str] = [
        "",
        "=" * 90,
        "LIBROS CON PRECIO DISMINUIDO RESPECTO AL DÍA ANTERIOR:",
        "=" * 90,
    ]

    for title, current_price, previous_price, historical_min in decreases[:10]:
        lines.extend(
            [
                f"Título: {title}",
                f"  Precio actual: {_fmt_price(current_price)}",
                f"  Precio del día anterior: {_fmt_price(previous_price)}",
                f"  Precio mínimo histórico: {_fmt_price(historical_min)}",
                "",
            ]
        )

    return "\n".join(lines)
