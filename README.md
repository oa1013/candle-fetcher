# Candle Fetcher

A Python project for fetching MT5 / FTMO candle data, filtering it by trading session, comparing candle CSVs, and finding calm or volatile market regimes.

The project supports:

* MetaTrader 5 / FTMO candle fetching
* New York session filtering
* London session filtering
* Asia session filtering
* All sessions filtering
* Custom date ranges
* Year filters
* Month filters
* Week filters
* Day filters
* Custom raw CSV names
* Custom processed CSV names
* Flexible timeframe settings, with `1m` as the normal default
* CSV comparison
* Calm / normal / volatile / extreme CSV labels
* Calmest or most volatile year, month, week, or day detection

## Project Workflow

Each runner notebook can fetch candles directly from MetaTrader 5 and then process the data.

The main workflow is:

```text
MT5 / FTMO → data/raw/ → data/processed/ → comparison / regime analysis
```

Example:

```text
MT5 / FTMO
  ↓
data/raw/
  ↓
notebooks/01_new_york_runner.ipynb
  ↓
data/processed/new_york/
```

The period regime finder can also work like this:

```text
MT5 / FTMO or existing CSV
  ↓
notebooks/06_period_regime_finder.ipynb
  ↓
calmest / most volatile year, month, week, or day
```

## Folder Structure

```text
candle-fetcher/
│
├── data/
│   ├── raw/
│   ├── processed/
│   │   ├── new_york/
│   │   ├── london/
│   │   ├── asia/
│   │   └── all_sessions/
│   └── comparisons/
│       ├── tables/
│       └── reports/
│
├── notebooks/
│   ├── 01_new_york_runner.ipynb
│   ├── 02_london_runner.ipynb
│   ├── 03_asia_runner.ipynb
│   ├── 04_all_sessions_runner.ipynb
│   ├── 05_csv_comparison_runner.ipynb
│   └── 06_period_regime_finder.ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── loaders.py
│   ├── date_filters.py
│   ├── session_filters.py
│   ├── exports.py
│   ├── pipeline.py
│   ├── mt5_fetcher.py
│   ├── regime_analysis.py
│   ├── csv_comparison.py
│   ├── comparison_exports.py
│   ├── comparison_formatting.py
│   ├── regime_period_filter.py
│   └── utils/
│       ├── file_naming.py
│       └── timeframes.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

## Notebooks

### `01_new_york_runner.ipynb`

Fetches raw candles from MT5 / FTMO, then filters candles to the New York session.

### `02_london_runner.ipynb`

Fetches raw candles from MT5 / FTMO, then filters candles to the London session.

### `03_asia_runner.ipynb`

Fetches raw candles from MT5 / FTMO, then filters candles to the Asia session.

### `04_all_sessions_runner.ipynb`

Fetches raw candles from MT5 / FTMO, then keeps all candles with no session time filter.

### `05_csv_comparison_runner.ipynb`

Compares two or more processed CSV files.

It can help identify whether selected CSV files look:

* calm
* normal
* volatile
* extreme

It also creates similarity tables so different CSVs can be compared against each other.

### `06_period_regime_finder.ipynb`

Finds the calmest or most volatile year, month, week, or day from candle data.

The notebook can either:

* use an existing CSV file
* fetch fresh candles from MetaTrader 5 / FTMO first

You can control:

* symbol
* timeframe
* date range
* period type: year, month, week, or day
* regime type: calm or volatile
* number of results to show
* custom output names

## Source Files

### `src/config.py`

Stores project paths, default settings, and session settings.

### `src/mt5_fetcher.py`

Connects to MetaTrader 5, fetches raw candle data, and saves it into `data/raw/`.

It supports custom raw CSV names through:

```python
RAW_OUTPUT_NAME = "my_custom_raw_file"
```

If `RAW_OUTPUT_NAME` is left as `None`, the project creates an automatic raw filename.

### `src/loaders.py`

Loads candle CSV files.

### `src/date_filters.py`

Filters candles by date range, years, months, weeks, days, and weekdays.

### `src/session_filters.py`

Filters candles by New York, London, Asia, or all sessions.

### `src/exports.py`

Builds output filenames and saves processed CSV files.

It supports custom processed CSV names through:

```python
OUTPUT_NAME = "my_custom_processed_file"
```

If `OUTPUT_NAME` is left as `None`, the project creates an automatic processed filename.

### `src/pipeline.py`

Connects the full session filtering workflow together.

### `src/regime_analysis.py`

Calculates candle behavior metrics such as:

* average range
* median range
* return volatility
* tick volume
* spread behavior

It uses those metrics to classify CSV files as:

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

### `src/comparison_formatting.py`

Formats comparison tables so they are easier to read.

It makes the regime summary and pairwise comparison tables more user-friendly.

### `src/regime_period_filter.py`

Finds calm or volatile periods inside a candle CSV.

It supports:

* calmest year
* calmest month
* calmest week
* calmest day
* most volatile year
* most volatile month
* most volatile week
* most volatile day

### `src/utils/file_naming.py`

Contains helper functions for building cleaner CSV file paths and filenames.

### `src/utils/timeframes.py`

Normalizes timeframe inputs.

For example:

```python
"1m" → "M1"
"5m" → "M5"
"1h" → "H1"
```

This allows the notebooks to use simple timeframe inputs while still working correctly with MT5.

## Data Folders

Raw MT5 / FTMO candle files are saved here:

```text
data/raw/
```

Processed session files are saved here:

```text
data/processed/
```

Comparison outputs are saved here:

```text
data/comparisons/tables/
data/comparisons/reports/
```

CSV files are ignored by Git so broker data is not uploaded to GitHub.

## Custom CSV Naming

Runner notebooks support custom CSV names.

For raw MT5 / FTMO CSVs:

```python
RAW_OUTPUT_NAME = "my_raw_mt5_file"
```

For processed session CSVs:

```python
OUTPUT_NAME = "my_processed_session_file"
```

For period regime finder result tables:

```python
OUTPUT_NAME = "my_period_regime_results"
```

If these are left as `None`, the project uses automatic filenames.

## Flexible Timeframes

Runner notebooks use `1m` as the normal default.

Example:

```python
TIMEFRAME = "1m"
```

Other supported examples include:

```python
TIMEFRAME = "5m"
TIMEFRAME = "15m"
TIMEFRAME = "30m"
TIMEFRAME = "1h"
TIMEFRAME = "4h"
TIMEFRAME = "1d"
```

The project converts these into MT5-style timeframe labels internally.

## CSV Comparison Workflow

The CSV comparison runner is:

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

## Period Regime Finder

The period regime finder can scan candle data and rank periods by volatility.

The period regime finder runner is:

```text
notebooks/06_period_regime_finder.ipynb
```

Example settings:

```python
PERIOD = "month"
REGIME = "calm"
```

This finds the calmest months.

```python
PERIOD = "week"
REGIME = "volatile"
```

This finds the most volatile weeks.

Supported periods:

* year
* month
* week
* day

Supported regimes:

* calm
* volatile

## Important Note About Regimes

The calm, normal, volatile, and extreme labels are relative to the files or periods being compared.

For CSV comparison, the tool decides which selected CSVs are calmer or more volatile compared with the other selected CSVs.

For the period regime finder, the tool decides which years, months, weeks, or days are calmer or more volatile compared with the other periods inside the selected candle data.

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

MetaTrader 5 must be open and logged into the correct FTMO / broker account before running MT5 fetches.

The project is designed for research and data preparation.

It does not place trades.
