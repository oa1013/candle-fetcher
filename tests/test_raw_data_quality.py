import pandas as pd
import pytest

from src import data_quality


def make_candles():
    timestamps = pd.date_range(
        "2025-01-15 14:30:00",
        periods=3,
        freq="1min",
        tz="UTC",
    )

    return pd.DataFrame({
        "datetime": timestamps,
        "mt5_time_raw": [
            int(t.timestamp()) for t in timestamps
        ],
        "open": [20000.25, 20003.25, 20005.25],
        "high": [20010.75, 20012.75, 20015.75],
        "low": [19998.50, 20000.50, 20002.50],
        "close": [20003.25, 20005.25, 20008.25],
        "tick_volume": [100, 0, 120],
        "spread": [15, 15, 15],
        "real_volume": [0, 0, 0],
    })


def test_valid_raw_candles():
    candles = make_candles()

    result = data_quality.validate_raw_m1_candles(
        candles
    )

    assert result["total_candles"] == 3
    assert result["invalid_timestamp_rows"] == 0
    assert result["non_minute_aligned_rows"] == 0
    assert result["invalid_ohlc_rows"] == 0
    assert result["invalid_ohlc_relationship_rows"] == 0
    assert result["negative_volume_rows"] == 0
    assert result["negative_spread_rows"] == 0
    assert result["duplicate_timestamp_rows"] == 0
    assert result["is_chronologically_sorted"] is True
    assert result["zero_tick_volume_rows"] == 1
    assert result["zero_real_volume_rows"] == 3


def test_invalid_ohlc_values_detected():
    candles = make_candles()

    candles.loc[0, "open"] = float("nan")
    candles.loc[1, "close"] = float("inf")

    result = data_quality.validate_raw_m1_candles(
        candles
    )

    assert result["invalid_ohlc_rows"] == 2


def test_invalid_ohlc_relationships_detected():
    candles = make_candles()

    candles.loc[0, "high"] = 19990.0
    candles.loc[1, "low"] = 20020.0

    result = data_quality.validate_raw_m1_candles(
        candles
    )

    assert result["invalid_ohlc_relationship_rows"] == 2


def test_negative_volume_and_spread_detected():
    candles = make_candles()

    candles.loc[0, "tick_volume"] = -10
    candles.loc[1, "real_volume"] = -5
    candles.loc[2, "spread"] = -15

    result = data_quality.validate_raw_m1_candles(
        candles
    )

    assert result["negative_volume_rows"] == 2
    assert result["negative_spread_rows"] == 1


def test_non_minute_aligned_timestamp_detected():
    candles = make_candles()

    candles.loc[1, "datetime"] += pd.Timedelta(
        seconds=30
    )

    result = data_quality.validate_raw_m1_candles(
        candles
    )

    assert result["non_minute_aligned_rows"] == 1


def test_missing_and_invalid_timestamps_detected():
    candles = make_candles()

    candles["datetime"] = [
        None,
        "invalid timestamp",
        "2025-01-15T14:32:00Z",
    ]

    result = data_quality.validate_raw_m1_candles(
        candles
    )

    assert result["invalid_timestamp_rows"] == 2


def test_naive_timestamps_detected():
    candles = make_candles()

    candles["datetime"] = (
        candles["datetime"].dt.tz_localize(None)
    )

    result = data_quality.validate_raw_m1_candles(
        candles
    )

    assert result["invalid_timestamp_rows"] == 3


def test_duplicate_timestamps_detected():
    candles = make_candles()

    candles.loc[1, "datetime"] = (
        candles.loc[0, "datetime"]
    )

    result = data_quality.validate_raw_m1_candles(
        candles
    )

    assert result["duplicate_timestamp_rows"] == 2


def test_unsorted_timestamps_detected():
    candles = make_candles().iloc[::-1]

    result = data_quality.validate_raw_m1_candles(
        candles
    )

    assert result["is_chronologically_sorted"] is False


def test_missing_required_column_rejected():
    candles = make_candles().drop(
        columns=["tick_volume"]
    )

    with pytest.raises(ValueError, match="tick_volume"):
        data_quality.validate_raw_m1_candles(
            candles
        )


def test_original_observations_not_modified():
    candles = make_candles()
    candles.loc[0, "spread"] = -15

    original = candles.copy(deep=True)

    data_quality.validate_raw_m1_candles(candles)

    pd.testing.assert_frame_equal(
        candles,
        original,
    )
