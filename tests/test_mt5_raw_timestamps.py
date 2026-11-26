import pandas as pd
import pytest

from src.mt5_fetcher import rates_to_dataframe


@pytest.mark.parametrize(
    "raw_time, expected_utc, ftmo_clock",
    [
        (
            "2025-01-15T14:30:00Z",
            "2025-01-15T14:30:00Z",
            False,
        ),
        (
            "2025-01-15T16:30:00Z",
            "2025-01-15T14:30:00Z",
            True,
        ),
        (
            "2025-07-15T16:30:00Z",
            "2025-07-15T13:30:00Z",
            True,
        ),
    ],
    ids=[
        "standard_utc",
        "ftmo_winter",
        "ftmo_summer",
    ],
)
def test_original_mt5_timestamp_preserved(
    raw_time,
    expected_utc,
    ftmo_clock,
):
    original_timestamp = int(
        pd.Timestamp(raw_time).timestamp()
    )

    rates = [
        {
            "time": original_timestamp,
            "open": 20000.25,
            "high": 20005.75,
            "low": 19998.50,
            "close": 20003.25,
            "tick_volume": 0,
            "spread": 15,
            "real_volume": 0,
        }
    ]

    result = rates_to_dataframe(
        rates,
        ftmo_athens_clock=ftmo_clock,
    )

    assert len(result) == 1

    assert "mt5_time_raw" in result.columns

    assert pd.api.types.is_integer_dtype(
        result["mt5_time_raw"]
    )

    assert (
        result.iloc[0]["mt5_time_raw"]
        == original_timestamp
    )

    assert (
        result.iloc[0]["datetime"]
        == pd.Timestamp(expected_utc)
    )

    for column in [
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
        "real_volume",
    ]:
        assert result.iloc[0][column] == rates[0][column]


def test_empty_result_preserves_timestamp_column():
    result = rates_to_dataframe([])

    assert result.empty
    assert "mt5_time_raw" in result.columns