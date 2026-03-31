# BuscaLibre Price Tracker

An application to track and monitor book prices on BuscaLibre.cl, specifically focused on detecting price decreases and recording price history for analysis.

## What does it do?

This application performs the following main functions:

1. **Daily price tracking**: Extracts current book prices from a specific list on BuscaLibre.cl
2. **Historical storage**: Saves all collected prices in a SQLite database to maintain a complete history
3. **Change detection**: Identifies when book prices have decreased compared to the previous day
4. **Historical low analysis**: Determines which books are currently at their lowest price ever recorded
5. **Detailed reports**: Generates clear reports on price decreases and historical lows

## How does it work?

### Architecture

The application is structured into the following main components:

- `main.py`: Application entry point
- `tracker/price_tracker.py`: Contains the main tracking, storage, and analysis logic
- `tracker/models.py`: Defines the data structures used (currently empty, maintained for future expansion)
- `buscalibre_prices.sqlite`: SQLite database that stores the entire price history
- `test_price_decreases.py`: Test script to validate the decrease detection logic

### Workflow

1. **Initialization**: When running the application, the SQLite database is initialized if it doesn't exist
2. **Data extraction**: The application retrieves current price data from BuscaLibre.cl via web scraping
3. **Storage**: Prices are saved in the `book_prices` table with the current date
4. **Comparison**: Today's prices are compared with yesterday's to detect changes
5. **Decrease detection**: Books whose prices have dropped compared to the previous day are identified
6. **Historical analysis**: Checks which books are at their all-time lowest price ever recorded
7. **Tabular report**: Displays a summary of findings in the console using formatted tables with pandas for better readability
8. **Meaningful comparisons**: For books at their historical low, a price comparison between today and the last recorded price is shown to identify recent movements

### Database

The application uses a SQLite database (`buscalibre_prices.sqlite`) with two main tables:

#### `book_prices`
- `id`: Primary key
- `title`: Book title
- `price`: Recorded price
- `date`: Record date
- `created_at`: Creation timestamp
- Unique constraint: `(title, date)` to prevent duplicates of the same book on the same date

#### `price_changes`
- `id`: Primary key
- `title`: Book title
- `change_type`: Change type ("Increased", "Decreased", "New product")
- `difference`: Absolute price difference
- `new_price`: New price after the change
- `date`: Change date
- `created_at`: Creation timestamp

## Requirements

- Python 3.x
- Python libraries:
  - requests
  - beautifulsoup4 (bs4)
  - sqlite3 (included in Python standard library)

To install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python main.py
```

Run validation tests:
```bash
python test_price_decreases.py
```

## Important notes

1. **Historical data**: The SQLite database contains irreproducible data (historical prices), so it is essential to keep it versioned in Git to preserve the history when switching between machines.

2. **Debug files**: The application creates a `debug.html` file during execution to facilitate scraping debugging. This file is intentionally excluded from versioning via `.gitignore`.

3. **Execution frequency**: To get the most value from this application, it is recommended to run it daily (e.g., via cron or Task Scheduler) to capture day-to-day price changes.

4. **Error handling**: If the website is unavailable or changes its structure, the application has a fallback mode that uses demo data to show that the system works correctly.

## Customization

To monitor a different list of books on BuscaLibre.cl, modify the `URL` constant in the `PriceTracker` class within `tracker/price_tracker.py`:

```python
URL: str = "https://www.buscalibre.cl/v2/pendientes_1722693_l.html"
```

## License

This project is under the MIT License - see the LICENSE file for more details.
