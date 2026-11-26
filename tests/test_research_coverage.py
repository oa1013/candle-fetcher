import pandas as pd
import pytest

from src import data_quality


def make_candles(values):
    return pd.DataFrame({
        "datetime": pd.to_datetime(
            values,
            utc=True,
        )
    })


def report(candles, start, end):
    return data_quality.build_research_coverage_report(
        candles,
        start_utc=pd.Timestamp(start),
        end_utc_exclusive=pd.Timestamp(end),
    )


def test_daily_and_monthly_coverage():
    candles = make_candles([
        "2025-01-31T23:59:00Z",
        "2025-03-01T00:00:00Z",
    ])

    result = report(
        candles,
        "2025-01-31T23:58:00Z",
        "2025-03-01T00:02:00Z",
    )

    daily = result["daily"]
    monthly = result["monthly"]

    assert len(daily) == 30
    assert len(monthly) == 3

    assert daily["recorded_candles"].sum() == 2
    assert monthly["recorded_candles"].sum() == 2

    assert monthly["recorded_candles"].tolist() == [
        1, 0, 1
    ]

    assert result["summary"]["recorded_candles"] == 2


def test_leading_internal_and_trailing_gaps():
    candles = make_candles([
        "2025-01-15T14:32:00Z",
        "2025-01-15T14:35:00Z",
    ])

    result = report(
        candles,
        "2025-01-15T14:30:00Z",
        "2025-01-15T14:38:00Z",
    )

    gaps = result["gaps"]

    assert gaps["gap_type"].tolist() == [
        "leading",
        "internal",
        "trailing",
    ]

    assert gaps["unobserved_minutes"].tolist() == [
        2, 2, 2
    ]

    assert result["summary"]["requested_calendar_minutes"] == 8
    assert result["summary"]["recorded_candles"] == 2
    assert result["summary"]["unobserved_minutes"] == 6


def test_gap_boundaries():
    candles = make_candles([
        "2025-01-15T14:30:00Z",
        "2025-01-15T14:33:00Z",
    ])

    result = report(
        candles,
        "2025-01-15T14:30:00Z",
        "2025-01-15T14:34:00Z",
    )

    gap = result["gaps"].iloc[0]

    assert gap["gap_start_utc"] == pd.Timestamp(
        "2025-01-15T14:31:00Z"
    )

    assert gap["gap_end_utc_exclusive"] == pd.Timestamp(
        "2025-01-15T14:33:00Z"
    )

    assert gap["unobserved_minutes"] == 2


def test_completely_unavailable_period():
    candles = make_candles([])

    result = report(
        candles,
        "2025-01-01T00:00:00Z",
        "2025-01-04T00:00:00Z",
    )

    assert len(result["daily"]) == 3

    assert result["daily"][
        "recorded_candles"
    ].tolist() == [0, 0, 0]

    assert result["summary"]["recorded_candles"] == 0
    assert result["summary"]["unobserved_minutes"] == 4320

    assert len(result["gaps"]) == 1

    assert result["gaps"].iloc[0][
        "gap_type"
    ] == "entire_period"

    assert result["summary"]["first_datetime_utc"] is None
    assert result["summary"]["last_datetime_utc"] is None


def test_fully_observed_period():
    candles = make_candles([
        "2025-01-15T14:30:00Z",
        "2025-01-15T14:31:00Z",
        "2025-01-15T14:32:00Z",
    ])

    result = report(
        candles,
        "2025-01-15T14:30:00Z",
        "2025-01-15T14:33:00Z",
    )

    assert result["gaps"].empty
    assert result["summary"]["unobserved_minutes"] == 0
    assert result["summary"]["recorded_candles"] == 3


def test_partial_day_coverage():
    candles = make_candles([
        "2025-01-15T14:30:00Z",
        "2025-01-15T14:32:00Z",
    ])

    result = report(
        candles,
        "2025-01-15T14:30:00Z",
        "2025-01-15T14:35:00Z",
    )

    daily = result["daily"].iloc[0]

    assert daily["requested_calendar_minutes"] == 5
    assert daily["recorded_candles"] == 2
    assert daily["unobserved_minutes"] == 3


def test_empty_requested_window():
    candles = make_candles([])

    result = report(
        candles,
        "2025-01-01T00:00:00Z",
        "2025-01-01T00:00:00Z",
    )

    assert result["daily"].empty
    assert result["monthly"].empty
    assert result["gaps"].empty

    assert result["summary"][
        "requested_calendar_minutes"
    ] == 0


def test_market_closure_not_assumed():
    candles = make_candles([
        "2025-01-17T20:00:00Z",
        "2025-01-20T01:00:00Z",
    ])

    result = report(
        candles,
        "2025-01-17T20:00:00Z",
        "2025-01-20T01:01:00Z",
    )

    assert result["summary"][
        "expected_trading_minutes"
    ] is None

    assert result["summary"][
        "confirmed_missing_trading_minutes"
    ] is None

    assert result["gaps"].iloc[0][
        "classification"
    ] == "unverified"


@pytest.mark.parametrize(
    "values",
    [
        [
            "2025-01-15T14:30:00Z",
            "2025-01-15T14:30:00Z",
        ],
        [
            "2025-01-15T14:32:00Z",
            "2025-01-15T14:30:00Z",
        ],
        ["2025-01-15T14:30:30Z"],
        ["2025-01-15T14:29:00Z"],
        ["2025-01-15T14:35:00Z"],
        [None],
    ],
)
def test_invalid_observations_rejected(values):
    candles = make_candles(values)

    with pytest.raises(ValueError):
        report(
            candles,
            "2025-01-15T14:30:00Z",
            "2025-01-15T14:35:00Z",
        )


def test_naive_timestamps_rejected():
    candles = make_candles([
        "2025-01-15T14:30:00Z",
    ])

    candles["datetime"] = (
        candles["datetime"].dt.tz_localize(None)
    )

    with pytest.raises(ValueError):
        report(
            candles,
            "2025-01-15T14:30:00Z",
            "2025-01-15T14:35:00Z",
        )


def test_original_observations_not_modified():
    candles = make_candles([
        "2025-01-15T14:30:00Z",
        "2025-01-15T14:32:00Z",
    ])

    original = candles.copy(deep=True)

    report(
        candles,
        "2025-01-15T14:30:00Z",
        "2025-01-15T14:35:00Z",
    )

    pd.testing.assert_frame_equal(
        candles,
        original,
        check_exact=True,
    )
