import pandas as pd
import pytest

from src import data_quality


def make_candles(timestamps):

    timestamps = pd.to_datetime(
        timestamps,
        utc=True,
    )

    return pd.DataFrame({
        "datetime": timestamps,
        "open": 20000.25,
        "high": 20010.50,
        "low": 19995.25,
        "close": 20005.25,
        "tick_volume": 100,
        "spread": 15,
        "real_volume": 0,
    })


def hourly_block(start, periods=48):

    return pd.date_range(
        start=start,
        periods=periods,
        freq="h",
        tz="UTC",
    )


def minute_block(start, periods=180):

    return pd.date_range(
        start=start,
        periods=periods,
        freq="min",
        tz="UTC",
    )


def validate(candles):

    return data_quality.validate_historical_timeframe(
        candles
    )


def test_dense_minute_data():

    candles = make_candles(
        minute_block("2025-01-15 14:30")
    )

    result = validate(candles)

    assert result["classification"] == (
        "minute_level_evidence"
    )

    assert result["total_observations"] == 180
    assert result["suspected_hourly_rows"] == 0
    assert result["has_minute_level_evidence"] is True
    assert result["consecutive_minute_intervals"] == 179
    assert result["longest_minute_run"] == 180


def test_hourly_data_detected():

    candles = make_candles(
        hourly_block("2021-02-08 00:00")
    )

    result = validate(candles)

    assert result["classification"] == (
        "suspected_hourly"
    )

    assert result["suspected_hourly_rows"] == 48
    assert result["has_minute_level_evidence"] is False

    assert len(
        result["suspected_hourly_regions"]
    ) == 1


def test_mixed_timeframe_transition():

    hourly = hourly_block(
        "2021-09-12 07:00",
        periods=48,
    )

    minute = minute_block(
        "2021-09-14 06:31",
        periods=180,
    )

    candles = make_candles(
        hourly.append(minute)
    )

    result = validate(candles)

    assert result["classification"] == (
        "possible_mixed_timeframe"
    )

    assert result["total_observations"] == 228

    assert result["suspected_hourly_rows"] == 48

    assert result["first_non_hourly_utc"] == (
        "2021-09-14T06:31:00+00:00"
    )

    region = result["suspected_hourly_regions"][0]

    assert region["first_datetime_utc"] == (
        "2021-09-12T07:00:00+00:00"
    )

    assert region["last_datetime_utc"] == (
        "2021-09-14T06:00:00+00:00"
    )

    assert region["observation_count"] == 48


def test_hourly_region_after_minute_data():

    minute = minute_block(
        "2024-06-10 08:01",
        periods=180,
    )

    hourly = hourly_block(
        "2024-06-11 00:00",
        periods=48,
    )

    candles = make_candles(
        minute.append(hourly)
    )

    result = validate(candles)

    assert result["classification"] == (
        "possible_mixed_timeframe"
    )

    assert result["suspected_hourly_rows"] == 48


def test_multiple_hourly_regions():

    first = hourly_block(
        "2023-01-02 00:00",
        periods=48,
    )

    minute = minute_block(
        "2023-01-05 09:01",
        periods=180,
    )

    second = hourly_block(
        "2023-01-09 00:00",
        periods=48,
    )

    candles = make_candles(
        first.append(minute).append(second)
    )

    result = validate(candles)

    assert result["classification"] == (
        "possible_mixed_timeframe"
    )

    assert result["suspected_hourly_rows"] == 96

    assert len(
        result["suspected_hourly_regions"]
    ) == 2


def test_hourly_region_with_weekend_gap():

    first = hourly_block(
        "2021-02-04 00:00",
        periods=46,
    )

    second = hourly_block(
        "2021-02-08 00:00",
        periods=24,
    )

    candles = make_candles(
        first.append(second)
    )

    result = validate(candles)

    assert result["classification"] == (
        "suspected_hourly"
    )

    assert result["suspected_hourly_rows"] == 70


def test_minute_data_with_market_closure():

    first = minute_block(
        "2025-01-17 18:00",
        periods=180,
    )

    second = minute_block(
        "2025-01-19 23:05",
        periods=180,
    )

    candles = make_candles(
        first.append(second)
    )

    result = validate(candles)

    assert result["classification"] == (
        "minute_level_evidence"
    )

    assert result["suspected_hourly_rows"] == 0
    assert result["longest_minute_run"] == 180


def test_daily_spacing_not_classified_as_hourly():

    timestamps = pd.date_range(
        "2024-01-01",
        periods=90,
        freq="D",
        tz="UTC",
    )

    result = validate(
        make_candles(timestamps)
    )

    assert result["classification"] == (
        "insufficient_evidence"
    )

    assert result["suspected_hourly_rows"] == 0


def test_short_hourly_sample():

    candles = make_candles(
        hourly_block(
            "2021-02-08 00:00",
            periods=5,
        )
    )

    result = validate(candles)

    assert result["classification"] == (
        "insufficient_evidence"
    )

    assert result["has_minute_level_evidence"] is False


def test_empty_dataset():

    candles = make_candles([])

    result = validate(candles)

    assert result["classification"] == (
        "no_observations"
    )

    assert result["total_observations"] == 0
    assert result["suspected_hourly_rows"] == 0
    assert result["first_non_hourly_utc"] is None


def test_original_data_not_modified():

    candles = make_candles(
        minute_block("2025-01-15 14:30")
    )

    original = candles.copy(deep=True)

    validate(candles)

    pd.testing.assert_frame_equal(
        candles,
        original,
        check_exact=True,
    )


def test_missing_datetime_column():

    candles = pd.DataFrame({
        "close": [20000.25],
    })

    with pytest.raises(ValueError):

        validate(candles)


@pytest.mark.parametrize(
    "problem",
    [
        "duplicate",
        "unsorted",
        "non_minute_aligned",
        "missing_timestamp",
        "naive_timezone",
    ],
)
def test_invalid_timestamps_rejected(problem):

    candles = make_candles(
        minute_block("2025-01-15 14:30")
    )

    if problem == "duplicate":

        candles.loc[1, "datetime"] = (
            candles.loc[0, "datetime"]
        )

    elif problem == "unsorted":

        candles = candles.iloc[::-1].copy()

    elif problem == "non_minute_aligned":

        candles.loc[0, "datetime"] += (
            pd.Timedelta(seconds=15)
        )

    elif problem == "missing_timestamp":

        candles.loc[0, "datetime"] = pd.NaT

    elif problem == "naive_timezone":

        candles["datetime"] = (
            candles["datetime"].dt.tz_localize(None)
        )

    with pytest.raises(ValueError):

        validate(candles)


def test_spacing_alone_does_not_prove_timeframe():

    candles = make_candles(
        minute_block("2025-01-15 14:30")
    )

    result = validate(candles)

    assert result["native_m1_proven"] is False

    assert result[
        "cross_timeframe_verification_performed"
    ] is False
