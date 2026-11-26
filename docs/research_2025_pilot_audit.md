# 2025 Historical Research Pilot Audit

## Audit date

26 November 2026

## Extraction configuration

- Instrument: US100.cash
- Timeframe: Native M1
- Broker: FTMO
- Server: FTMO-Server3
- MT5 package version: 5.0.5735
- Source commit: 75fcaaf780f41d959fd707454e2e42f6e732d753
- Calendar timezone: UTC
- Start: 2025-01-01 00:00 UTC, inclusive
- End: 2026-01-01 00:00 UTC, exclusive
- Chunk size: 31 days
- Session filtering: None

## Live extraction results

- Exported candles: 348793
- Months with observations: 12
- Days with observations: 312
- Days without observations: 53
- Invalid timestamps: 0
- Duplicate timestamps in final CSV: 0
- Identical duplicates consolidated: 8
- Conflicting timestamps: 0
- Invalid OHLC observations: 0
- Invalid OHLC relationships: 0
- Timestamp inconsistencies: 0
- SHA-256 checksum verification: Passed

## Historical coverage

- Requested calendar minutes: 525600
- Recorded candles: 348793
- Unobserved calendar minutes: 176807
- Internal gaps: 277
- Leading gaps: 1
- Trailing gaps: 1
- Total reported gaps: 279

First corrected observation:
2025-01-01 23:05:00 UTC

Last corrected observation:
2025-12-31 21:49:00 UTC

## Original datasets examined

Raw dataset:

data/raw/us100_cash_M1_raw_all_sessions_range_2025-01-01_to_2026-01-01.csv

Processed dataset:

data/processed/all_sessions/2025_full_year.csv

## Initial timestamp comparison

Both original datasets contained 348793 candles.

When compared directly against corrected UTC timestamps:

- Matching timestamps: 324223
- Original-only timestamps: 24570
- New-only timestamps: 24570
- Candles with mismatched values: 324222
- Total field mismatches: 1831449

## Original MT5 clock comparison

The new extraction preserves the original integer MT5
timestamp in the mt5_time_raw column.

The original datasets were compared against these
uncorrected MT5 timestamp labels.

Results for both original datasets:

- Matching observations: 348793
- Original-only observations: 0
- New-only observations: 0
- Open mismatches: 0
- High mismatches: 0
- Low mismatches: 0
- Close mismatches: 0
- Tick volume mismatches: 0
- Spread mismatches: 0
- Real volume mismatches: 0
- Total field mismatches: 0
- Exact observation match: True

## Confirmed timestamp discrepancy

The original datasets stored MT5 server-clock timestamps
incorrectly labelled as UTC.

The corrected extraction applies the established
FTMO-Server3 clock convention:

FTMO server wall time = New York wall time + 7 hours.

The resulting UTC corrections for 2025 were:

- UTC+2 correction: 119252 candles
- UTC+3 correction: 229541 candles

All original OHLCV and spread observations matched
the new extraction exactly after alignment by the
original MT5 clock.

## Implications for previous research

Historical analyses based on incorrectly labelled
timestamps may require recalculation, particularly:

- Session filtering
- Hourly volatility
- Market opening analysis
- Session range analysis
- Time-dependent regime analysis
- Session-based backtesting

Original datasets must be retained for reproducibility
and must not be silently overwritten.

## Limitations

The exact observation match establishes reproducibility
against the original datasets.

It does not independently establish absolute historical
market completeness.

Unobserved calendar minutes may include scheduled
closures, holidays, maintenance or unavailable history.

A verified historical broker trading calendar is still
required to distinguish these categories conclusively.

The confirmed timestamp results apply to the examined
2025 datasets and FTMO-Server3 extraction.

Other historical years require separate validation.

## Conclusion

The 2025 historical pilot passed its extraction,
data integrity, timestamp consistency, checksum and
original observation comparison checks.

Proceed with extraction and validation of 2021, 2022,
2023, 2024 and 2026 year-to-date.
