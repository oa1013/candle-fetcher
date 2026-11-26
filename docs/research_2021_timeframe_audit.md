# 2021 Historical Timeframe Integrity Audit

## Audit date

26 November 2026

## Extraction configuration

- Instrument: US100.cash
- Requested timeframe: M1
- Broker: FTMO
- Server: FTMO-Server3
- Calendar timezone: UTC
- Source commit: 64731f6b92c991b4f2aa660a460efcf7e578bece
- Original chunk size: 31 days
- Session filtering: None

## Initial extraction

- Total returned observations: 109121
- Invalid timestamps: 0
- Duplicate timestamps: 0
- Identical duplicates consolidated: 8
- Conflicting timestamps: 0
- Invalid OHLC observations: 0
- Timestamp inconsistencies: 0
- Checksum verification: Passed
- Reported historical gaps: 3699

Despite passing conventional integrity checks, the
dataset exhibited exceptionally sparse historical
coverage before September 2021.

## Smaller request verification

The following periods were extracted again using
one-day chunks instead of 31-day chunks:

| Period | Original | Smaller requests | Matching |
|---|---:|---:|---:|
| 2021-02-08 to 2021-02-13 | 105 | 105 | 105 |
| 2021-08-09 to 2021-08-14 | 109 | 109 | 109 |
| 2021-10-11 to 2021-10-16 | 6710 | 6710 | 6710 |

No additional timestamps were recovered.

This indicates that the original request size was not
responsible for the sparse data in the tested periods.

## Observed historical timeframe transition

First non-hourly observation:

2021-09-14 06:31:00 UTC

Before the transition, observations occurred exclusively
at hourly timestamps.

After the transition, observations predominantly occurred
at consecutive one-minute intervals.

## Full-year H1 comparison

A separate H1 extraction returned 5393 observations.

### Before transition

- Observations returned by M1 request: 3615
- Shared H1 timestamps: 3615
- Exact open matches: 3615
- Exact high matches: 3615
- Exact low matches: 3615
- Exact close matches: 3615
- Exact tick volume matches: 3614
- Exact spread matches: 3615
- Exact real volume matches: 3615
- Complete exact H1 matches: 3614
- Exact matching percentage: 99.9723 percent

One observation differed only in tick volume.

All 3615 pre-transition observations must be excluded
from verified minute-level research datasets.

### After transition

- Returned observations: 105506
- Shared H1 timestamps: 1701
- Complete exact H1 matches: 0
- Consecutive one-minute intervals: 105423

The absence of exact H1 matches and the predominantly
one-minute spacing support minute-level provenance.

## Independent cross-timeframe validation

Complete groups of 60 consecutive minute observations
were temporarily aggregated and compared against
independently requested H1 candles.

- Complete hourly groups: 1620
- Comparable H1 observations: 1620
- Open matches: 1620
- High matches: 1620
- Low matches: 1620
- Close matches: 1620
- Tick volume matches: 1620
- Real volume matches: 1620
- Complete exact matches: 1620

Aggregation was performed exclusively for verification.

No original historical files were modified, resampled,
interpolated or reconstructed.

## Dataset classification

The original 2021 M1-request export contains mixed
timeframe observations and must not be distributed
as an entirely native M1 dataset.

Original returned observations: 109121

Pre-transition observations to quarantine: 3615

Post-transition M1 candidate observations: 105506

Observed M1 transition: 2021-09-14 06:31:00 UTC

## Required engineering changes

Introduce a Historical Timeframe Integrity Validator.

The validator should:

- Detect suspicious hourly timestamp concentrations.
- Identify changes in historical observation density.
- Report possible mixed timeframe regions.
- Distinguish requested timeframe from observed evidence.
- Support independent higher-timeframe verification.
- Prevent misleading native M1 dataset publication.
- Preserve original extraction evidence.
- Record unavailable minute-level historical periods.

## Limitations

The underlying reason why the M1 interface returned
H1-like observations has not been established.

The behaviour could originate from the broker's
historical storage or the MT5 history delivery system.

The observed transition applies to this extraction
and does not establish a permanent broker history limit.

Cross-timeframe validation supports the post-transition
minute-level observations but does not guarantee
absolute historical market completeness.

No missing M1 candles may be fabricated from H1 data.

## Conclusion

Conventional candle integrity and timestamp validation
alone cannot establish historical timeframe integrity.

The 2021 dataset requires explicit timeframe
classification and separation before delivery.

Original extraction evidence must remain unchanged.
