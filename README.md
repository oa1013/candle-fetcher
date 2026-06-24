# Candle Fetcher

A Python project for fetching MT5 / FTMO candle data, filtering it by trading session, comparing candle CSVs, finding calm or volatile market regimes, and detecting volatility jumps.

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
* Volatility jump detection
* Volatility jump comparison between CSVs
* Local news/event matching near volatility jumps
* Interactive browser dashboard with light, dark, and auto theme modes

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

The volatility jump workflow is:

```text
processed CSV
  ↓
volatility jump detection
  ↓
jump tables / reports / browser dashboard
  ↓
optional CSV comparison and news/event matching
```

## Folder Structure

```text
candle-fetcher/
│
├── apps/
│   ├── candle_dashboard_app.py
│   ├── volatility_jump_app.py
│   ├── assets/
│   │   └── app_styles.css
│   └── pages/
│       ├── 01_CSV_Comparison.py
│       ├── 02_Period_Regime_Finder.py
│       ├── 03_Volatility_Jump_Runner.py
│       └── 04_News_Events.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   │   ├── new_york/
│   │   ├── london/
│   │   ├── asia/
│   │   └── all_sessions/
│   │
│   ├── comparisons/
│   │   ├── tables/
│   │   └── reports/
│   │
│   ├── jumps/
│   │   ├── tables/
│   │   ├── reports/
│   │   └── charts/
│   │
│   └── news/
│       └── market_news_events.example.csv
│
├── notebooks/
│   ├── 01_new_york_runner.ipynb
│   ├── 02_london_runner.ipynb
│   ├── 03_asia_runner.ipynb
│   ├── 04_all_sessions_runner.ipynb
│   ├── 05_csv_comparison_runner.ipynb
│   ├── 06_period_regime_finder.ipynb
│   └── 07_volatility_jump_runner.ipynb
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
│   ├── volatility_jumps.py
│   ├── volatility_jump_exports.py
│   ├── volatility_jump_comparison.py
│   ├── news_matcher.py
│   ├── theme_manager.py
│   ├── dashboard_ui.py
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

### `07_volatility_jump_runner.ipynb`

Detects the biggest volatility jumps inside a candle CSV.

The notebook can show:

* top volatility jumps
* jump scores
* price move percentages
* jump regimes
* user-friendly jump tables
* saved jump reports

## Dashboard

The project includes a Streamlit dashboard for running the main candle research tools from one interface:

```text
apps/candle_dashboard_app.py
```

Run the dashboard with:

```bash
streamlit run apps/candle_dashboard_app.py
```

Dashboard pages:

* **CSV Comparison**  
  Compare processed candle CSV files, review regime labels, similarity scores, pairwise differences, and download comparison tables.

* **Period Regime Finder**  
  Find the calmest or most volatile year, month, week, or day from candle data and download the ranked period table.

* **Volatility Jump Runner**  
  Detect volatility jumps, compare jump profiles, match nearby news or event data, and download jump tables.

* **News / Events**  
  View, upload, search, and download news/event CSV files used for volatility jump context.

The dashboard supports:

* light mode
* dark mode
* auto mode
* consistent theme selection across every dashboard page
* styled sidebar and dashboard cards
* CSV download buttons for dashboard results

The notebooks are still kept as backup/testing runners, but the dashboard is now the main interface for regular analysis.

The older standalone volatility jump app is still available here:

```text
apps/volatility_jump_app.py
```

Run it with:

```bash
streamlit run apps/volatility_jump_app.py
```

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

### `src/volatility_jumps.py`

Detects volatility jumps inside candle data.

It calculates:

* candle range
* candle body
* rolling range baseline
* rolling ATR-style baseline
* jump score
* range-to-baseline ratio
* price move percentage
* jump regime

### `src/volatility_jump_exports.py`

Saves volatility jump outputs into:

```text
data/jumps/tables/
data/jumps/reports/
```

It can save:

* top jump tables
* markdown jump reports

### `src/volatility_jump_comparison.py`

Compares volatility jump behavior between multiple CSV files.

It can compare:

* total rows
* total jumps
* jump rate percentage
* largest jump score
* average jump score
* median jump score
* average price move percentage
* largest price move percentage

### `src/news_matcher.py`

Matches volatility jumps to nearby local news or event records.

This does not prove causation. It only shows events that happened near the detected jump time.

### `src/theme_manager.py`

Controls light, dark, and auto theme options for the Streamlit dashboard.

### `src/dashboard_ui.py`

Provides reusable Streamlit dashboard UI helpers, including:

* shared CSS loading
* dashboard cards
* status cards
* page headers
* footer notes
* CSV download buttons

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

Volatility jump outputs are saved here:

```text
data/jumps/tables/
data/jumps/reports/
data/jumps/charts/
```

News/event templates are stored here:

```text
data/news/
```

CSV files and generated outputs are ignored by Git so broker data and generated analysis files are not uploaded to GitHub.

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

## Volatility Jump Runner

The volatility jump runner detects sudden volatility spikes inside candle CSV data.

The notebook runner is:

```text
notebooks/07_volatility_jump_runner.ipynb
```

The main dashboard page is:

```text
apps/pages/03_Volatility_Jump_Runner.py
```

Run it through the dashboard with:

```bash
streamlit run apps/candle_dashboard_app.py
```

The dashboard page can show:

* total rows
* detected jumps
* largest jump score
* average top jump score
* price chart with jump markers
* rolling jump score chart
* top volatility jump table
* CSV jump comparison table
* CSV jump comparison chart
* related news/events table
* CSV download buttons for jump results, comparisons, and news matches

## Volatility Jump Outputs

Volatility jump outputs are saved into:

```text
data/jumps/tables/
data/jumps/reports/
data/jumps/charts/
```

Generated jump output files are ignored by Git.

The project keeps the folders using `.gitkeep` files.

## News / Event Matching

The Volatility Jump Runner can match nearby news or events to detected volatility jumps.

The template file is:

```text
data/news/market_news_events.example.csv
```

To create a local working news file, copy it:

```powershell
Copy-Item data/news/market_news_events.example.csv data/news/market_news_events.csv -Force
```

The local working news file is:

```text
data/news/market_news_events.csv
```

This file is for local research and should not be committed.

Expected news/event columns:

```text
datetime
headline
event_type
importance
source
url
symbol
```

Important: news matching does not prove that the news caused the jump. It only shows events that happened near the jump time.

## News / Events Dashboard Page

The dashboard includes a dedicated News / Events page:

```text
apps/pages/04_News_Events.py
```

This page can:

* load the local news/events CSV
* fall back to the example news/events CSV if the local file is missing
* upload a replacement news/events CSV
* search event rows
* download the filtered news/events table

Run it through the main dashboard:

```bash
streamlit run apps/candle_dashboard_app.py
```

## Important Note About Regimes

The calm, normal, volatile, and extreme labels are relative to the files or periods being compared.

For CSV comparison, the tool decides which selected CSVs are calmer or more volatile compared with the other selected CSVs.

For the period regime finder, the tool decides which years, months, weeks, or days are calmer or more volatile compared with the other periods inside the selected candle data.

For volatility jump detection, jump scores are calculated relative to the recent rolling volatility baseline.

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

The dashboard uses:

```text
streamlit
plotly
```

## Notes

MetaTrader 5 must be open and logged into the correct FTMO / broker account before running MT5 fetches.

The project is designed for research and data preparation.

It does not place trades.

The app and notebooks are for analysis only, not financial advice.
