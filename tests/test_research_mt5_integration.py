from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from src import research_export
from src import mt5_fetcher


UTC = timezone.utc

AS_OF = datetime(
    2026, 11, 26, 22, 15, 37,
    tzinfo=UTC,
)


@pytest.fixture
def connection(monkeypatch):
    initialize = Mock()
    shutdown = Mock()

    account = Mock(
        return_value=SimpleNamespace(
            company="FTMO Global Markets Ltd",
            server="FTMO-Server3",
            login=123456789,
        )
    )

    symbol = Mock(
        return_value=SimpleNamespace(
            visible=True,
            digits=2,
            point=0.01,
        )
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
        account,
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "symbol_info",
        symbol,
    )

    candles = pd.DataFrame({
        "datetime": pd.to_datetime(
            ["2025-01-15T14:30:00Z"],
            utc=True,
        ),
        "mt5_time_raw": [1736958600],
        "open": [20000.25],
        "high": [20010.75],
        "low": [19998.50],
        "close": [20003.25],
        "tick_volume": [100],
        "spread": [15],
        "real_volume": [0],
    })

    def fake_fetch(**kwargs):
        kwargs["diagnostics"].append({
            "status": "returned",
            "rows_returned": 1,
        })

        kwargs["duplicate_diagnostics"].update({
            "identical_duplicates": 0,
            "conflicting_timestamps": 0,
        })

        return candles.copy(deep=True)

    fetch = Mock(side_effect=fake_fetch)

    monkeypatch.setattr(
        mt5_fetcher,
        "fetch_candles_by_range",
        fetch,
    )

    return SimpleNamespace(
        initialize=initialize,
        shutdown=shutdown,
        account=account,
        symbol=symbol,
        fetch=fetch,
        candles=candles,
    )


def test_native_m1_annual_fetch(connection):
    result = research_export.fetch_research_year(
        year=2025,
        as_of_utc=AS_OF,
    )

    connection.initialize.assert_called_once()
    connection.shutdown.assert_called_once()
    connection.fetch.assert_called_once()

    kwargs = connection.fetch.call_args.kwargs

    assert kwargs["symbol"] == "US100.cash"

    assert kwargs["timeframe_mt5"] == (
        mt5_fetcher.TIMEFRAME_MAP["M1"]
    )

    assert kwargs["start_utc"] == datetime(
        2025, 1, 1, tzinfo=UTC
    )

    assert kwargs["end_utc_exclusive"] == datetime(
        2026, 1, 1, tzinfo=UTC
    )

    assert kwargs["ftmo_athens_clock"] is True
    assert kwargs["chunk_days"] == 31

    pd.testing.assert_frame_equal(
        result["candles"],
        connection.candles,
    )


def test_actual_provenance_collected(connection):
    result = research_export.fetch_research_year(
        year=2025,
        as_of_utc=AS_OF,
    )

    provenance = result["provenance"]

    assert provenance["symbol"] == "US100.cash"
    assert provenance["timeframe"] == "M1"

    assert provenance["broker"] == (
        "FTMO Global Markets Ltd"
    )

    assert provenance["server"] == "FTMO-Server3"
    assert provenance["timestamp_mode"] == "ftmo_server"
    assert provenance["symbol_digits"] == 2
    assert provenance["symbol_point"] == 0.01

    assert "login" not in provenance
    assert "password" not in provenance
    assert "account_id" not in provenance


def test_diagnostics_preserved(connection):
    result = research_export.fetch_research_year(
        year=2025,
        as_of_utc=AS_OF,
    )

    assert len(result["chunk_diagnostics"]) == 1

    assert result["chunk_diagnostics"][0][
        "status"
    ] == "returned"

    assert result["duplicate_diagnostics"] == {
        "identical_duplicates": 0,
        "conflicting_timestamps": 0,
    }


def test_unverified_server_rejected(connection):
    connection.account.return_value.server = (
        "FTMO-Demo"
    )

    with pytest.raises(RuntimeError, match="(?i)server"):
        research_export.fetch_research_year(
            year=2025,
            as_of_utc=AS_OF,
        )

    connection.fetch.assert_not_called()
    connection.shutdown.assert_called_once()


def test_missing_account_rejected(connection):
    connection.account.return_value = None

    with pytest.raises(RuntimeError, match="(?i)account"):
        research_export.fetch_research_year(
            year=2025,
            as_of_utc=AS_OF,
        )

    connection.fetch.assert_not_called()
    connection.shutdown.assert_called_once()


def test_connection_closed_after_fetch_failure(connection):
    connection.fetch.side_effect = RuntimeError(
        "Simulated historical fetch failure"
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated historical fetch failure",
    ):
        research_export.fetch_research_year(
            year=2025,
            as_of_utc=AS_OF,
        )

    connection.shutdown.assert_called_once()


def test_current_year_cutoff_forwarded(connection):
    connection.candles["datetime"] = pd.to_datetime(
        ["2026-11-26T22:14:00Z"],
        utc=True,
    )

    connection.candles["mt5_time_raw"] = [
        int(
            datetime(
                2026, 11, 27, 0, 14, tzinfo=UTC
            ).timestamp()
        )
    ]

    research_export.fetch_research_year(
        year=2026,
        as_of_utc=AS_OF,
    )

    kwargs = connection.fetch.call_args.kwargs

    assert kwargs["end_utc_exclusive"] == datetime(
        2026, 11, 26, 22, 15, tzinfo=UTC
    )


def test_configurable_chunk_size(connection):
    research_export.fetch_research_year(
        year=2025,
        as_of_utc=AS_OF,
        chunk_days=7,
    )

    assert connection.fetch.call_args.kwargs[
        "chunk_days"
    ] == 7
