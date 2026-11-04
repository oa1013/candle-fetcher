"""Regression tests for FTMO timestamp-mode compatibility."""

from pathlib import Path
from types import SimpleNamespace
from contextlib import ExitStack
from unittest.mock import patch

import pandas as pd
import pytest

from src.mt5_fetcher import (
    MT5FetchConfig,
    fetch_raw_candles,
)


@pytest.mark.parametrize(
    "mode, expected_enabled",
    [
        pytest.param(
            "ftmo_server",
            True,
            id="new_ftmo_server",
        ),
        pytest.param(
            "ftmo_athens",
            True,
            id="legacy_ftmo_athens",
        ),
        pytest.param(
            "auto",
            True,
            id="automatic_ftmo",
        ),
        pytest.param(
            "utc",
            False,
            id="standard_utc",
        ),
    ],
)
def test_ftmo_timestamp_mode_compatibility(
    mode,
    expected_enabled,
):
    """New and legacy modes must preserve the correct behaviour."""

    config = MT5FetchConfig(
        symbol="US100.cash",
        timeframe="M1",
        start_date="2024-01-11",
        end_date="2024-01-11",
        timestamp_mode=mode,
    )

    sample = pd.DataFrame({
        "datetime": pd.to_datetime(
            ["2024-01-11T14:10:00Z"],
            utc=True,
        ),
    })

    with ExitStack() as stack:

        stack.enter_context(
            patch("src.mt5_fetcher.initialize_mt5")
        )

        stack.enter_context(
            patch("src.mt5_fetcher.shutdown_mt5")
        )

        stack.enter_context(
            patch("src.mt5_fetcher.ensure_symbol_available")
        )

        stack.enter_context(
            patch(
                "src.mt5_fetcher.mt5.account_info",
                return_value=SimpleNamespace(
                    server="FTMO-Server3"
                ),
            )
        )

        fetch = stack.enter_context(
            patch(
                "src.mt5_fetcher.fetch_candles_by_range",
                return_value=sample,
            )
        )

        stack.enter_context(
            patch(
                "src.mt5_fetcher.save_raw_candles_to_csv",
                return_value=Path(
                    "data/raw/test_mock.csv"
                ),
            )
        )

        result = fetch_raw_candles(config)

    assert fetch.call_count == 1

    # Existing internal keyword is intentionally
    # preserved until compatibility is verified.
    assert (
        fetch.call_args.kwargs["ftmo_athens_clock"]
        is expected_enabled
    )

    assert result["rows_saved"] == 1
