from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from src import mt5_fetcher
from src import research_export


UTC = timezone.utc


def make_extraction():

    return {
        "year": 2025,

        "requested_start_utc": (
            "2025-01-01T00:00:00+00:00"
        ),

        "requested_end_utc_exclusive": (
            "2026-01-01T00:00:00+00:00"
        ),

        "chunk_days": 31,

        "provenance": {
            "symbol": "US100.cash",
            "timeframe": "M1",
            "broker": "FTMO Global Markets Ltd",
            "server": "FTMO-Server3",
            "timestamp_mode": "ftmo_server",
            "symbol_digits": 2,
            "symbol_point": 0.01,
        },
    }


@pytest.fixture
def terminal(monkeypatch):

    initialize = Mock()
    shutdown = Mock()

    account = SimpleNamespace(
        company="FTMO Global Markets Ltd",
        server="FTMO-Server3",
    )

    symbol = SimpleNamespace(
        digits=2,
        point=0.01,
        visible=True,
    )

    monkeypatch.setattr(
        mt5_fetcher,
        "initialize_mt5",
        initialize,
    )

    monkeypatch.setattr(
        mt5_fetcher,
        "shutdown_mt5",
        shutdown,
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "account_info",
        Mock(return_value=account),
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "symbol_info",
        Mock(return_value=symbol),
    )

    monkeypatch.setattr(
        mt5_fetcher,
        "ensure_symbol_available",
        Mock(),
    )

    candles = pd.DataFrame({
        "datetime": pd.to_datetime(
            ["2025-01-02T00:00:00Z"],
            utc=True,
        ),

        "mt5_time_raw": [
            int(pd.Timestamp(
                "2025-01-02T02:00:00Z"
            ).timestamp())
        ],

        "open": [20000.0],
        "high": [20020.0],
        "low": [19990.0],
        "close": [20010.0],
        "tick_volume": [3000],
        "spread": [15],
        "real_volume": [0],
    })

    fetch = Mock(return_value=candles)

    monkeypatch.setattr(
        mt5_fetcher,
        "fetch_candles_by_range",
        fetch,
    )

    return {
        "initialize": initialize,
        "shutdown": shutdown,
        "account": account,
        "symbol": symbol,
        "fetch": fetch,
        "candles": candles,
    }


def fetch_reference(extraction):

    return (
        research_export
        .fetch_research_h1_reference(extraction)
    )


def test_fetches_correct_h1_reference(terminal):

    result = fetch_reference(
        make_extraction()
    )

    arguments = terminal[
        "fetch"
    ].call_args.kwargs

    assert arguments["symbol"] == "US100.cash"

    assert arguments["timeframe_mt5"] == (
        mt5_fetcher.mt5.TIMEFRAME_H1
    )

    assert arguments["start_utc"] == datetime(
        2025, 1, 1, tzinfo=UTC
    )

    assert arguments[
        "end_utc_exclusive"
    ] == datetime(
        2026, 1, 1, tzinfo=UTC
    )

    assert arguments["chunk_days"] == 31
    assert arguments["ftmo_athens_clock"] is True

    pd.testing.assert_frame_equal(
        result["candles"],
        terminal["candles"],
    )

    assert result["provenance"]["timeframe"] == "H1"

    assert result["provenance"]["symbol"] == "US100.cash"

    assert result["provenance"]["server"] == "FTMO-Server3"

    terminal["initialize"].assert_called_once()
    terminal["shutdown"].assert_called_once()


def test_current_incomplete_hour_excluded(terminal):

    extraction = make_extraction()

    extraction["year"] = 2026

    extraction["requested_start_utc"] = (
        "2026-01-01T00:00:00+00:00"
    )

    extraction["requested_end_utc_exclusive"] = (
        "2026-11-26T22:57:00+00:00"
    )

    terminal["fetch"].return_value = (
        mt5_fetcher.empty_candle_dataframe()
    )

    result = fetch_reference(extraction)

    arguments = terminal[
        "fetch"
    ].call_args.kwargs

    assert arguments[
        "end_utc_exclusive"
    ] == datetime(
        2026, 11, 26, 22, 0,
        tzinfo=UTC,
    )

    assert result[
        "requested_end_utc_exclusive"
    ] == "2026-11-26T22:00:00+00:00"


@pytest.mark.parametrize(
    "field,value",
    [
        ("company", "Another Broker"),
        ("server", "FTMO-Demo"),
    ],
)
def test_connection_provenance_mismatch(
    terminal,
    field,
    value,
):

    setattr(
        terminal["account"],
        field,
        value,
    )

    with pytest.raises(ValueError):

        fetch_reference(
            make_extraction()
        )

    terminal["fetch"].assert_not_called()
    terminal["shutdown"].assert_called_once()


@pytest.mark.parametrize(
    "field,value",
    [
        ("digits", 3),
        ("point", 0.001),
    ],
)
def test_symbol_specification_mismatch(
    terminal,
    field,
    value,
):

    setattr(
        terminal["symbol"],
        field,
        value,
    )

    with pytest.raises(ValueError):

        fetch_reference(
            make_extraction()
        )

    terminal["fetch"].assert_not_called()
    terminal["shutdown"].assert_called_once()


@pytest.mark.parametrize(
    "field,value",
    [
        ("symbol", "EURUSD"),
        ("timeframe", "H1"),
        ("timestamp_mode", "utc"),
        ("server", "Unknown-Server"),
    ],
)
def test_invalid_source_provenance(
    terminal,
    field,
    value,
):

    extraction = make_extraction()

    extraction["provenance"][field] = value

    with pytest.raises(ValueError):

        fetch_reference(extraction)

    terminal["fetch"].assert_not_called()


def test_empty_reference_preserved(terminal):

    terminal["fetch"].return_value = (
        mt5_fetcher.empty_candle_dataframe()
    )

    result = fetch_reference(
        make_extraction()
    )

    assert result["candles"].empty
    assert result["rows_fetched"] == 0


def test_no_complete_hour_available(terminal):

    extraction = make_extraction()

    extraction["requested_end_utc_exclusive"] = (
        "2025-01-01T00:30:00+00:00"
    )

    result = fetch_reference(extraction)

    assert result["candles"].empty
    assert result["rows_fetched"] == 0

    terminal["fetch"].assert_not_called()


def test_fetch_failure_closes_connection(terminal):

    terminal["fetch"].side_effect = RuntimeError(
        "Historical reference unavailable."
    )

    with pytest.raises(RuntimeError):

        fetch_reference(
            make_extraction()
        )

    terminal["shutdown"].assert_called_once()


def test_reference_diagnostics_retained(terminal):

    def simulated_fetch(**kwargs):

        kwargs["diagnostics"].append({
            "status": "returned",
            "rows_returned": 1,
        })

        kwargs["duplicate_diagnostics"][
            "identical_duplicates"
        ] = 2

        return terminal["candles"]

    terminal["fetch"].side_effect = (
        simulated_fetch
    )

    result = fetch_reference(
        make_extraction()
    )

    assert len(
        result["chunk_diagnostics"]
    ) == 1

    assert result["duplicate_diagnostics"][
        "identical_duplicates"
    ] == 2

    assert result["rows_fetched"] == 1


def test_missing_provenance_rejected(terminal):

    extraction = make_extraction()

    del extraction["provenance"]["broker"]

    with pytest.raises(ValueError):

        fetch_reference(extraction)

    terminal["fetch"].assert_not_called()
