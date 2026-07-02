# BuscaLibre Price Tracker

An application to track and monitor book prices on BuscaLibre.cl, specifically focused on detecting price decreases and recording price history for analysis.

## What does it do?

1. **Daily price tracking**: Extracts current book prices from a specific list on BuscaLibre.cl
2. **Historical storage**: Saves all collected prices in a SQLite database
3. **Change detection**: Identifies when prices have changed compared to the last recorded price
4. **Historical low analysis**: Determines which books are currently at their lowest price ever recorded
5. **Detailed reports**: Generates clear reports with formatted tables

## Architecture

- `main.py`: Application entry point with command-line argument support
- `tracker/price_tracker.py`: Workflow orchestrator
- `tracker/scraper.py`: Scraping logic with automatic retries
- `tracker/repository.py`: SQLite database access
- `tracker/analyzer.py`: Pure price comparison and historical-low detection logic
- `tracker/reporter.py`: Report formatting as strings
- `tracker/models.py`: Data structures
- `tracker/config.py`: Centralized configuration (environment variables + CLI)
- `tracker/exceptions.py`: Domain exceptions
- `tracker/check_price_decreases.py`: Diagnostic tool to inspect the production DB
- `tracker/create_test_data.py`: Generates deterministic test data
- `buscalibre_prices.sqlite`: SQLite database with price history

## Installation

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

It is recommended to run it daily (e.g., via cron) to capture price changes.

### Configuration

Configuration can be provided via environment variables or command-line arguments. CLI arguments take precedence over environment variables.

Environment variables:

- `BUSCALIBRE_URL`: BuscaLibre list URL to scrape
- `BUSCALIBRE_DB_PATH`: Path to the SQLite file
- `BUSCALIBRE_TIMEOUT`: HTTP request timeout in seconds
- `BUSCALIBRE_RETRIES`: Number of retries on HTTP failures

CLI arguments:

```bash
python main.py --url https://www.buscalibre.cl/v2/pendientes_1722693_l.html \
               --db-path ./buscalibre_prices.sqlite \
               --timeout 20 \
               --retries 5
```

### Helper tools

Check price decreases in the existing database:

```bash
python -m tracker.check_price_decreases
```

Generate deterministic test data for yesterday:

```bash
python -m tracker.create_test_data
```

## Tests

```bash
pytest
```

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
- The scraper includes automatic retries with backoff for transient errors (429, 500, 502, 503, 504).

## License

MIT
