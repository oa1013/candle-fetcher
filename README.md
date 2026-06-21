# Candle Fetcher

A Python project for fetching MT5 / FTMO candle data and filtering it by trading session.

The project supports:

* New York session
* London session
* Asia session
* All sessions
* Custom date ranges
* Year filters
* Month filters
* Week filters
* Day filters

## Project Workflow

Each runner notebook can fetch candles directly from MetaTrader 5 and then process the data.

The workflow is:

```text
MT5 → data/raw/ → data/processed/
```

Example:

```text
MT5
  ↓
data/raw/
  ↓
notebooks/01_new_york_runner.ipynb
  ↓
data/processed/new_york/
```

## Folder Structure

```text
candle-fetcher/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│   ├── 01_new_york_runner.ipynb
│   ├── 02_london_runner.ipynb
│   ├── 03_asia_runner.ipynb
│   └── 04_all_sessions_runner.ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── loaders.py
│   ├── date_filters.py
│   ├── session_filters.py
│   ├── exports.py
│   ├── pipeline.py
│   └── mt5_fetcher.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

## Notebooks

### `01_new_york_runner.ipynb`

Fetches raw candles from MT5, then filters candles to the New York session.

### `02_london_runner.ipynb`

Fetches raw candles from MT5, then filters candles to the London session.

### `03_asia_runner.ipynb`

Fetches raw candles from MT5, then filters candles to the Asia session.

### `04_all_sessions_runner.ipynb`

Fetches raw candles from MT5, then keeps all sessions with no session time filter.

## Source Files

### `src/config.py`

Stores project paths, default settings, and session settings.

### `src/mt5_fetcher.py`

Connects to MetaTrader 5, fetches raw candle data, and saves it into `data/raw/`.

### `src/loaders.py`

Loads candle CSV files from `data/raw/`.

### `src/date_filters.py`

Filters candles by date range, years, months, weeks, days, and weekdays.

### `src/session_filters.py`

Filters candles by New York, London, Asia, or all sessions.

### `src/exports.py`

Builds output filenames and saves processed CSV files.

### `src/pipeline.py`

Connects the full processing workflow together.

## Data Folders

Raw MT5 candle files are saved here:

```text
data/raw/
```

Processed session files are saved here:

```text
data/processed/
```

CSV files are ignored by Git so broker data is not uploaded to GitHub.

## Requirements

Install requirements with:

```bash
python -m pip install -r requirements.txt
```

Recommended virtual environment setup:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Notes

MetaTrader 5 must be open and logged into the correct account before running the notebooks.

The project is designed for research and data preparation. It does not place trades.

## CSV Comparison Workflow

The project also includes a CSV comparison notebook:

```text
notebooks/05_csv_comparison_runner.ipynb
```

This notebook compares processed session CSV files and helps identify whether each file looks calm, normal, volatile, or extreme compared with the other selected files.

The comparison workflow is:

```text
data/processed/new_york/
data/processed/london/
data/processed/asia/
data/processed/all_sessions/
        ↓
notebooks/05_csv_comparison_runner.ipynb
        ↓
data/comparisons/
```

## Comparison Outputs

Comparison results are saved into:

```text
data/comparisons/tables/
data/comparisons/reports/
```

The comparison notebook can produce:

* regime summary tables
* pairwise similarity tables
* volatility scores
* calm / normal / volatile / extreme labels
* markdown comparison reports

## Comparison Source Files

### `src/regime_analysis.py`

Calculates candle behavior metrics such as average range, median range, return volatility, tick volume, and spread behavior.

It uses those metrics to classify each CSV as:

* calm
* normal
* volatile
* extreme

### `src/csv_comparison.py`

Compares two or more CSV files and calculates similarity percentages.

It can compare:

* New York vs London
* London vs Asia
* New York vs Asia
* one year vs another year
* one month vs another month
* two files from the same session

### `src/comparison_exports.py`

Saves comparison tables and markdown reports into the `data/comparisons/` folder.

## Important Note About Regimes

The calm, normal, volatile, and extreme labels are relative to the files being compared.

For example, if you compare New York, London, and Asia, the tool decides which of those files is calmest or most volatile compared with the others in that comparison group.

## Future Plans

In the future, this project may include a universal runner that can work with candle data from multiple trading platforms, not only MetaTrader 5.

The goal would be to keep the same workflow:

```text
trading platform → raw candle data → session filtering → comparison analysis
```

Possible future data sources could include:

* MetaTrader 5
* TradingView
* cTrader
* NinjaTrader
* Interactive Brokers
* Tradovate
* Sierra Chart
* Generic broker CSV exports

The idea is to build one universal runner that can load or fetch candle data from different platforms, normalize the data into the same candle format, and then reuse the existing session filters, regime analysis, and CSV comparison tools.
