import json

import pandas as pd
import pytest

from src import data_quality


def make_hourly():

    timestamps = pd.date_range(
        "2024-01-01 00:00",
        periods=24,
        freq="h",
        tz="UTC",
    )

    return pd.DataFrame({
        "datetime": timestamps,
        "open": 100.0,
        "high": 120.0,
        "low": 90.0,
        "close": 110.0,
        "tick_volume": 3000,
        "spread": 2,
        "real_volume": 0,
    })


def make_minute():

    timestamps = pd.date_range(
        "2024-01-02 00:00",
        periods=60,
        freq="min",
        tz="UTC",
    )

    prices = pd.Series(
        range(100, 160),
        dtype=float,
    )

    return pd.DataFrame({
        "datetime": timestamps,
        "open": prices,
        "high": prices + 2,
        "low": prices - 1,
        "close": prices + 0.5,
        "tick_volume": range(10, 70),
        "spread": 2,
        "real_volume": 0,
    })


def make_reference_hour():

    return pd.DataFrame({
        "datetime": [
            pd.Timestamp("2024-01-02T00:00:00Z")
        ],
        "open": [100.0],
        "high": [161.0],
        "low": [99.0],
        "close": [159.5],
        "tick_volume": [2370],
        "spread": [3],
        "real_volume": [0],
    })


def verify(m1, h1):

    return data_quality.verify_historical_timeframe(
        m1,
        h1,
    )


def test_genuine_minute_aggregation():

    result = verify(
        make_minute(),
        make_reference_hour(),
    )

    direct = result["direct_comparison"]
    aggregated = result["aggregation_comparison"]

    assert direct["shared_timestamps"] == 1
    assert direct["exact_matches"] == 0

    assert aggregated["complete_groups"] == 1
    assert aggregated["comparable_groups"] == 1
    assert aggregated["exact_matches"] == 1

    assert "spread" not in aggregated["field_matches"]


def test_hourly_observations_detected():

    hourly = make_hourly()

    result = verify(
        hourly,
        hourly.copy(),
    )

    direct = result["direct_comparison"]

    assert direct["shared_timestamps"] == 24
    assert direct["exact_matches"] == 24
    assert direct["ohlc_matches"] == 24

    assert result["aggregation_comparison"][
        "complete_groups"
    ] == 0

    region = result["suspected_hourly_regions"][0]

    assert region["observation_count"] == 24
    assert region["exact_matches"] == 24


def test_single_tick_volume_difference():

    m1 = make_hourly()
    h1 = make_hourly()

    h1.loc[0, "tick_volume"] += 1

    result = verify(m1, h1)

    direct = result["direct_comparison"]

    assert direct["exact_matches"] == 23
    assert direct["ohlc_matches"] == 24
    assert direct["field_matches"]["tick_volume"] == 23

    region = result["suspected_hourly_regions"][0]

    assert region["exact_matches"] == 23
    assert region["ohlc_matches"] == 24


def test_mixed_timeframe_verification():

    hourly = make_hourly()
    minute = make_minute()

    m1 = pd.concat(
        [hourly, minute],
        ignore_index=True,
    )

    h1 = pd.concat(
        [hourly, make_reference_hour()],
        ignore_index=True,
    )

    result = verify(m1, h1)

    assert result["total_observations"] == 84

    assert result["direct_comparison"][
        "shared_timestamps"
    ] == 25

    assert result["direct_comparison"][
        "exact_matches"
    ] == 24

    assert result["aggregation_comparison"][
        "exact_matches"
    ] == 1

    regions = result["suspected_hourly_regions"]

    assert len(regions) == 1
    assert regions[0]["observation_count"] == 24
    assert regions[0]["exact_matches"] == 24


def test_incomplete_hour_excluded():

    m1 = make_minute().drop(index=30)

    result = verify(
        m1,
        make_reference_hour(),
    )

    aggregated = result["aggregation_comparison"]

    assert aggregated["complete_groups"] == 0
    assert aggregated["comparable_groups"] == 0
    assert aggregated["exact_matches"] == 0


def test_aggregation_mismatch_reported():

    h1 = make_reference_hour()

    h1.loc[0, "high"] += 5

    result = verify(
        make_minute(),
        h1,
    )

    aggregated = result["aggregation_comparison"]

    assert aggregated["complete_groups"] == 1
    assert aggregated["comparable_groups"] == 1
    assert aggregated["exact_matches"] == 0
    assert aggregated["field_matches"]["high"] == 0
    assert aggregated["field_matches"]["open"] == 1


def test_missing_h1_reference():

    result = verify(
        make_minute(),
        make_reference_hour().iloc[:0],
    )

    assert result["reference_observations"] == 0

    assert result["direct_comparison"][
        "shared_timestamps"
    ] == 0

    assert result["aggregation_comparison"][
        "complete_groups"
    ] == 1

    assert result["aggregation_comparison"][
        "comparable_groups"
    ] == 0

    assert result["warnings"]


def test_empty_m1_dataset():

    result = verify(
        make_minute().iloc[:0],
        make_reference_hour(),
    )

    assert result["total_observations"] == 0
    assert result["direct_comparison"]["exact_matches"] == 0

    assert result["aggregation_comparison"][
        "complete_groups"
    ] == 0


def test_original_datasets_unchanged():

    m1 = make_minute()
    h1 = make_reference_hour()

    original_m1 = m1.copy(deep=True)
    original_h1 = h1.copy(deep=True)

    result = verify(m1, h1)

    pd.testing.assert_frame_equal(
        m1,
        original_m1,
        check_exact=True,
    )

    pd.testing.assert_frame_equal(
        h1,
        original_h1,
        check_exact=True,
    )

    json.dumps(result, allow_nan=False)

    assert result["native_m1_proven"] is False


@pytest.mark.parametrize(
    "problem",
    [
        "duplicate",
        "non_hour_aligned",
        "naive_timezone",
        "missing_field",
        "invalid_value",
    ],
)
def test_invalid_reference_rejected(problem):

    m1 = make_minute()
    h1 = make_reference_hour()

    if problem == "duplicate":

        h1 = pd.concat(
            [h1, h1],
            ignore_index=True,
        )

    elif problem == "non_hour_aligned":

        h1.loc[0, "datetime"] += pd.Timedelta(
            minutes=15
        )

    elif problem == "naive_timezone":

        h1["datetime"] = (
            h1["datetime"].dt.tz_localize(None)
        )

    elif problem == "missing_field":

        h1 = h1.drop(columns=["high"])

    elif problem == "invalid_value":

        h1.loc[0, "high"] = float("nan")

    with pytest.raises(ValueError):

        verify(m1, h1)


def test_short_hourly_region_direct_comparison():

    hourly = make_hourly().iloc[:5].copy()

    result = verify(
        hourly,
        hourly.copy(),
    )

    assert result["direct_comparison"][
        "exact_matches"
    ] == 5

    assert result["native_m1_proven"] is False

