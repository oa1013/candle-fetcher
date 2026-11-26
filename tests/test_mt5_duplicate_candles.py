from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.mt5_fetcher import (
    rates_to_dataframe,
    fetch_candles_by_range,
    TIMEFRAME_MAP,
)


START = datetime(
    2025, 1, 15, 0, 0,
    tzinfo=timezone.utc,
)

BOUNDARY = START + timedelta(days=1)
END = START + timedelta(days=2)


def make_candle(timestamp=START, close=20003.25):
    return {
        "time": int(timestamp.timestamp()),
        "open": 20000.25,
        "high": 20010.75,
        "low": 19998.50,
        "close": close,
        "tick_volume": 100,
        "spread": 15,
        "real_volume": 0,
    }


def test_identical_duplicates_consolidated():
    candle = make_candle()

    result = rates_to_dataframe(
        [candle, candle.copy()]
    )

    assert len(result) == 1


def test_identical_duplicates_counted():
    candle = make_candle()
    diagnostics = {}

    result = rates_to_dataframe(
        [candle, candle.copy()],
        duplicate_diagnostics=diagnostics,
    )

    assert len(result) == 1
    assert diagnostics["identical_duplicates"] == 1


def test_conflicting_prices_rejected():
    first = make_candle()
    second = make_candle(close=20008.25)

    with pytest.raises(ValueError, match="(?i)conflict"):
        rates_to_dataframe([first, second])


def test_conflicting_volume_rejected():
    first = make_candle()
    second = first.copy()
    second["tick_volume"] = 200

    with pytest.raises(ValueError, match="(?i)conflict"):
        rates_to_dataframe([first, second])


def test_identical_chunk_boundary_duplicates():
    candle = make_candle(BOUNDARY)
    diagnostics = {}

    with patch(
        "src.mt5_fetcher.mt5.copy_rates_range",
        side_effect=[
            [candle],
            [candle.copy()],
        ],
    ):
        result = fetch_candles_by_range(
            symbol="US100.cash",
            timeframe_mt5=TIMEFRAME_MAP["M1"],
            start_utc=START,
            end_utc_exclusive=END,
            chunk_days=1,
            duplicate_diagnostics=diagnostics,
        )

    assert len(result) == 1
    assert diagnostics["identical_duplicates"] == 1


def test_conflicting_chunk_boundary_duplicates():
    first = make_candle(BOUNDARY)
    second = make_candle(
        BOUNDARY,
        close=20008.25,
    )

    with patch(
        "src.mt5_fetcher.mt5.copy_rates_range",
        side_effect=[
            [first],
            [second],
        ],
    ):
        with pytest.raises(ValueError, match="(?i)conflict"):
            fetch_candles_by_range(
                symbol="US100.cash",
                timeframe_mt5=TIMEFRAME_MAP["M1"],
                start_utc=START,
                end_utc_exclusive=END,
                chunk_days=1,
            )


def test_conflict_evidence_preserved():
    from src.mt5_fetcher import CandleConflictError

    first = make_candle()
    second = make_candle(close=20008.25)

    diagnostics = {}

    with pytest.raises(CandleConflictError) as error:
        rates_to_dataframe(
            [first, second],
            duplicate_diagnostics=diagnostics,
        )

    evidence = error.value.conflicting_rows

    assert len(evidence) == 2

    assert set(evidence["close"]) == {
        first["close"],
        second["close"],
    }

    assert evidence["datetime"].nunique() == 1

    assert evidence["mt5_time_raw"].tolist() == [
        first["time"],
        second["time"],
    ]

    assert diagnostics["conflicting_timestamps"] == 1
    assert diagnostics["identical_duplicates"] == 0


def test_unique_candles_remain_unchanged():
    first = make_candle(START)
    second = make_candle(
        START + timedelta(minutes=1)
    )

    diagnostics = {}

    result = rates_to_dataframe(
        [second, first],
        duplicate_diagnostics=diagnostics,
    )

    assert len(result) == 2
    assert result["datetime"].is_monotonic_increasing
    assert diagnostics["identical_duplicates"] == 0
    assert diagnostics["conflicting_timestamps"] == 0

    for index, candle in enumerate([first, second]):
        assert result.iloc[index]["mt5_time_raw"] == candle["time"]

        for column in [
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "spread",
            "real_volume",
        ]:
            assert result.iloc[index][column] == candle[column]
