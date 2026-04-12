# BuscaLibre Price Tracker

An application to track and monitor book prices on BuscaLibre.cl, specifically focused on detecting price decreases and recording price history for analysis.

## What does it do?

1. **Daily price tracking**: Extracts current book prices from a specific list on BuscaLibre.cl
2. **Historical storage**: Saves all collected prices in a SQLite database
3. **Change detection**: Identifies when prices have changed compared to the last recorded price
4. **Historical low analysis**: Determines which books are currently at their lowest price ever recorded
5. **Detailed reports**: Generates clear reports with formatted tables

## Architecture

- `main.py`: Application entry point
- `tracker/price_tracker.py`: Tracking, storage, and analysis logic
- `tracker/models.py`: Data structures
- `check_price_decreases.py`: Diagnostic tool to inspect the production DB
- `buscalibre_prices.sqlite`: SQLite database with price history

## Usage

```bash
pip install -r requirements.txt
python main.py
```

It is recommended to run it daily (e.g., via cron) to capture price changes.

## Database

### `book_prices`
- `id`, `title`, `price`, `date`, `created_at`
- Unique constraint: `(title, date)`
- Indexes on `date` and `(title, date)`

### `price_changes`
- `id`, `title`, `change_type`, `difference`, `new_price`, `date`, `created_at`
- Index on `date`

## Important notes

- Prices are compared against the **last recorded price** for each book, not just yesterday. If a day is skipped, the comparison still works.
- If scraping fails, the application reports an error. No fake data is inserted into the database.

## Customization

Modify the `DEFAULT_URL` constant in `PriceTracker`:

```python
DEFAULT_URL: str = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"
```

## License

MIT
