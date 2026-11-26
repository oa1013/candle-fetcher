from datetime import datetime, timezone

import pandas as pd
import pytest

from src import data_quality


UTC = timezone.utc

START = datetime(2025, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 1, tzinfo=UTC)


def raw_seconds(value):
    return int(
        pd.Timestamp(value).timestamp()
    )


def make_candles():
    return pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-01-15T14:30:00Z",
            "2025-07-15T14:30:00Z",
        ], utc=True),

        "mt5_time_raw": [
            raw_seconds("2025-01-15T16:30:00Z"),
            raw_seconds("2025-07-15T17:30:00Z"),
        ],
    })


def validate(candles):
    return data_quality.validate_ftmo_timestamp_consistency(
        candles,
        start_utc=START,
        end_utc_exclusive=END,
    )


def test_correct_winter_and_summer_timestamps():
    result = validate(make_candles())

    assert result["total_candles"] == 2
    assert result["invalid_raw_timestamp_rows"] == 0
    assert result["invalid_corrected_timestamp_rows"] == 0
    assert result["undecodable_raw_timestamp_rows"] == 0
    assert result["timestamp_mismatch_rows"] == 0
    assert result["outside_requested_range_rows"] == 0
    assert result["is_consistent"] is True


def test_incorrect_timezone_conversion_detected():
    candles = make_candles()

    candles.loc[1, "datetime"] += pd.Timedelta(
        hours=1
    )

    result = validate(candles)

    assert result["timestamp_mismatch_rows"] == 1
    assert result["is_consistent"] is False


def test_fractional_raw_timestamp_rejected():
    candles = make_candles()

    candles["mt5_time_raw"] = (
        candles["mt5_time_raw"].astype(float)
    )

    candles.loc[0, "mt5_time_raw"] += 0.5

    result = validate(candles)

    assert result["invalid_raw_timestamp_rows"] == 1
    assert result["is_consistent"] is False


def test_missing_and_invalid_raw_timestamps():
    candles = make_candles()

    candles["mt5_time_raw"] = [
        None,
        "invalid",
    ]

    result = validate(candles)

    assert result["invalid_raw_timestamp_rows"] == 2
    assert result["is_consistent"] is False


def test_naive_corrected_timestamps_rejected():
    candles = make_candles()

    candles["datetime"] = (
        candles["datetime"].dt.tz_localize(None)
    )

    result = validate(candles)

    assert result["invalid_corrected_timestamp_rows"] == 2
    assert result["is_consistent"] is False


def test_us_daylight_saving_transitions():
    candles = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-03-07T14:30:00Z",
            "2025-03-10T14:30:00Z",
            "2025-10-31T14:30:00Z",
            "2025-11-03T14:30:00Z",
        ], utc=True),

        "mt5_time_raw": [
            raw_seconds("2025-03-07T16:30:00Z"),
            raw_seconds("2025-03-10T17:30:00Z"),
            raw_seconds("2025-10-31T17:30:00Z"),
            raw_seconds("2025-11-03T16:30:00Z"),
        ],
    })

    result = validate(candles)

    assert result["timestamp_mismatch_rows"] == 0
    assert result["is_consistent"] is True


@pytest.mark.parametrize(
    "raw_timestamp",
    [
        "2025-03-09T09:30:00Z",
        "2025-11-02T08:30:00Z",
    ],
)
def test_ambiguous_or_nonexistent_clock_rejected(
    raw_timestamp,
):
    candles = make_candles().iloc[[0]].copy()

    candles["mt5_time_raw"] = [
        raw_seconds(raw_timestamp)
    ]

    result = validate(candles)

    assert result["undecodable_raw_timestamp_rows"] == 1
    assert result["is_consistent"] is False


def test_annual_boundaries_enforced():
    candles = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2024-12-31T23:59:00Z",
            "2025-01-01T00:00:00Z",
            "2025-12-31T23:59:00Z",
            "2026-01-01T00:00:00Z",
        ], utc=True),

        "mt5_time_raw": [
            raw_seconds("2025-01-01T01:59:00Z"),
            raw_seconds("2025-01-01T02:00:00Z"),
            raw_seconds("2026-01-01T01:59:00Z"),
            raw_seconds("2026-01-01T02:00:00Z"),
        ],
    })

    result = validate(candles)

    assert result["timestamp_mismatch_rows"] == 0
    assert result["outside_requested_range_rows"] == 2
    assert result["is_consistent"] is False


def test_original_timestamps_not_modified():
    candles = make_candles()

    original = candles.copy(deep=True)

    validate(candles)

    pd.testing.assert_frame_equal(
        candles,
        original,
        check_exact=True,
    )


def test_missing_raw_timestamp_column_rejected():
    candles = make_candles().drop(
        columns=["mt5_time_raw"]
    )

    with pytest.raises(
        ValueError,
        match="mt5_time_raw",
    ):
        validate(candles)
