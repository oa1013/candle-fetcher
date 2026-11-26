from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pandas as pd
import pytest

from src.mt5_fetcher import (
    fetch_candles_by_range,
    TIMEFRAME_MAP,
)


START = datetime(
    2025, 1, 15, 14, 30,
    tzinfo=timezone.utc,
)

END = START + timedelta(minutes=3)


def make_rates():
    return [
        {
            "time": int(START.timestamp()),
            "open": 20000.25,
            "high": 20005.75,
            "low": 19998.50,
            "close": 20003.25,
            "tick_volume": 100,
            "spread": 15,
            "real_volume": 0,
        }
    ]


def test_successful_chunk_diagnostics():
    diagnostics = []

    with patch(
        "src.mt5_fetcher.mt5.copy_rates_range",
        return_value=make_rates(),
    ):
        result = fetch_candles_by_range(
            symbol="US100.cash",
            timeframe_mt5=TIMEFRAME_MAP["M1"],
            start_utc=START,
            end_utc_exclusive=END,
            diagnostics=diagnostics,
        )

    assert len(result) == 1
    assert len(diagnostics) == 1

    record = diagnostics[0]

    assert record["status"] == "returned"
    assert record["rows_returned"] == 1

    assert pd.Timestamp(
        record["requested_start_utc"]
    ) == pd.Timestamp(START)

    assert pd.Timestamp(
        record["requested_end_utc_exclusive"]
    ) == pd.Timestamp(END)

    assert pd.Timestamp(
        record["first_datetime_utc"]
    ) == pd.Timestamp(START)

    assert pd.Timestamp(
        record["last_datetime_utc"]
    ) == pd.Timestamp(START)

    assert record["mt5_error"] is None


def test_empty_chunk_diagnostics():
    diagnostics = []

    with patch(
        "src.mt5_fetcher.mt5.copy_rates_range",
        return_value=[],
    ):
        result = fetch_candles_by_range(
            symbol="US100.cash",
            timeframe_mt5=TIMEFRAME_MAP["M1"],
            start_utc=START,
            end_utc_exclusive=END,
            diagnostics=diagnostics,
        )

    assert result.empty
    assert len(diagnostics) == 1

    record = diagnostics[0]

    assert record["status"] == "empty"
    assert record["rows_returned"] == 0
    assert record["first_datetime_utc"] is None
    assert record["last_datetime_utc"] is None


def test_failed_chunk_diagnostics():
    diagnostics = []

    with patch(
        "src.mt5_fetcher.mt5.copy_rates_range",
        return_value=None,
    ), patch(
        "src.mt5_fetcher.mt5.last_error",
        return_value=(-1, "Simulated MT5 failure"),
    ):
        with pytest.raises(RuntimeError):
            fetch_candles_by_range(
                symbol="US100.cash",
                timeframe_mt5=TIMEFRAME_MAP["M1"],
                start_utc=START,
                end_utc_exclusive=END,
                diagnostics=diagnostics,
            )

    assert len(diagnostics) == 1

    record = diagnostics[0]

    assert record["status"] == "failed"
    assert record["rows_returned"] == 0
    assert record["mt5_error"][0] == -1
