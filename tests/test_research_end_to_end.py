import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from src import mt5_fetcher
from src.research_export import export_research_year
from src.exports import verify_research_checksum


UTC = timezone.utc

AS_OF = datetime(
    2026, 11, 26, 22, 15, 37,
    tzinfo=UTC,
)


MT5_DTYPE = np.dtype([
    ("time", "int64"),
    ("open", "float64"),
    ("high", "float64"),
    ("low", "float64"),
    ("close", "float64"),
    ("tick_volume", "int64"),
    ("spread", "int32"),
    ("real_volume", "int64"),
])


def make_rate(raw_clock, price=20000.25, volume=100):

    return (
        int(pd.Timestamp(raw_clock).timestamp()),
        price,
        price + 10,
        price - 5,
        price + 2,
        volume,
        15,
        0,
    )


def read_json(path):

    return json.loads(
        path.read_text(encoding="utf-8")
    )


@pytest.fixture
def terminal(monkeypatch):

    initialize = Mock(return_value=True)
    shutdown = Mock(return_value=True)

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "initialize",
        initialize,
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "shutdown",
        shutdown,
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "account_info",
        Mock(return_value=SimpleNamespace(
            company="FTMO Global Markets Ltd",
            server="FTMO-Server3",
            login=987654321,
        )),
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "symbol_info",
        Mock(return_value=SimpleNamespace(
            visible=True,
            digits=2,
            point=0.01,
        )),
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "last_error",
        Mock(return_value=(
            -1,
            "Private account information 987654321",
        )),
    )

    state = SimpleNamespace(
        rates=np.array([], dtype=MT5_DTYPE),
        initialize=initialize,
        shutdown=shutdown,
    )

    def copy_rates(
        symbol,
        timeframe,
        start,
        end,
    ):

        assert symbol == "US100.cash"

        if timeframe == mt5_fetcher.mt5.TIMEFRAME_H1:

            return np.array([], dtype=MT5_DTYPE)

        assert timeframe == (
            mt5_fetcher.TIMEFRAME_MAP["M1"]
        )

        assert start.tzinfo is not None
        assert end.tzinfo is not None

        # MT5 range requests include both endpoints.

        selected = (
            (state.rates["time"] >= int(start.timestamp()))
            & (state.rates["time"] <= int(end.timestamp()))
        )

        return state.rates[selected].copy()

    state.copy_rates = copy_rates

    state.fetch = Mock(
        side_effect=copy_rates
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "copy_rates_range",
        state.fetch,
    )

    return state


def test_native_annual_pipeline(
    tmp_path,
    terminal,
):

    terminal.rates = np.array([
        make_rate("2025-01-01T02:00:00Z"),
        make_rate("2025-02-01T02:00:00Z"),
        make_rate(
            "2025-07-15T17:30:00Z",
            price=21000.25,
            volume=0,
        ),
        make_rate("2026-01-01T01:59:00Z"),
        make_rate("2026-01-01T02:00:00Z"),
    ], dtype=MT5_DTYPE)

    original = terminal.rates.copy()

    result = export_research_year(
        year=2025,
        output_folder=tmp_path,
        as_of_utc=AS_OF,
        chunk_days=31,
    )

    csv_path = result["csv_path"]

    candles = pd.read_csv(
        csv_path,
        float_precision="round_trip",
    )

    expected_utc = pd.to_datetime([
        "2025-01-01T00:00:00Z",
        "2025-02-01T00:00:00Z",
        "2025-07-15T14:30:00Z",
        "2025-12-31T23:59:00Z",
    ], utc=True)

    actual_utc = pd.to_datetime(
        candles["datetime"],
        utc=True,
    )

    assert actual_utc.tolist() == (
        expected_utc.tolist()
    )

    assert candles["mt5_time_raw"].tolist() == (
        original["time"][:4].tolist()
    )

    for column in MT5_DTYPE.names:

        if column == "time":
            continue

        assert candles[column].tolist() == (
            original[column][:4].tolist()
        )

    assert pd.api.types.is_integer_dtype(
        candles["mt5_time_raw"]
    )

    assert len(candles) == 4

    assert verify_research_checksum(csv_path)

    assert result["checksum_verified"] is True

    metadata = read_json(
        result["metadata_path"]
    )

    assert metadata["rows_exported"] == 4

    assert metadata["duplicate_diagnostics"][
        "identical_duplicates"
    ] == 1

    assert metadata["timestamp_validation"][
        "is_consistent"
    ] is True

    assert metadata["data_quality"][
        "zero_tick_volume_rows"
    ] == 1

    assert metadata["coverage_summary"][
        "recorded_candles"
    ] == 4

    assert metadata["coverage_summary"][
        "unobserved_minutes"
    ] == 525596

    m1_requests = [
        call.args
        for call in terminal.fetch.call_args_list
        if call.args[1] == mt5_fetcher.mt5.TIMEFRAME_M1
    ]

    h1_requests = [
        call.args
        for call in terminal.fetch.call_args_list
        if call.args[1] == mt5_fetcher.mt5.TIMEFRAME_H1
    ]

    assert len(m1_requests) == 12
    assert len(h1_requests) == 12
    assert terminal.fetch.call_count == 24

    assert result["m1_export_path"] is None
    assert result["quarantine_path"] == csv_path
    assert csv_path.parent.name == "quarantine"

    assert metadata["requested_timeframe"] == "M1"
    assert metadata["timeframe"] == "unverified"

    assert "missing_h1_reference" in (
        result["timeframe_decision"]["blocking_reasons"]
    )

    assert "insufficient_minute_level_evidence" in (
        result["timeframe_decision"]["blocking_reasons"]
    )

    first_request = m1_requests[0]
    last_request = m1_requests[-1]

    assert first_request[2] == datetime(
        2025, 1, 1, 2, 0,
        tzinfo=UTC,
    )

    assert first_request[3] == datetime(
        2025, 2, 1, 2, 0,
        tzinfo=UTC,
    )

    assert last_request[3] == datetime(
        2026, 1, 1, 2, 0,
        tzinfo=UTC,
    )

    diagnostics = read_json(
        result["diagnostics_path"]
    )

    assert len(
        diagnostics["chunk_diagnostics"]
    ) == 12

    assert sum(
        record["rows_returned"]
        for record in diagnostics["chunk_diagnostics"]
    ) == 6

    assert diagnostics["failure"] is None

    np.testing.assert_array_equal(
        terminal.rates,
        original,
    )

    assert len(
        diagnostics["h1_reference"]["chunk_diagnostics"]
    ) == 12

    assert diagnostics["h1_reference"]["rows_fetched"] == 0

    assert terminal.initialize.call_count == 2
    assert terminal.shutdown.call_count == 2


def test_currently_forming_candle_excluded(
    tmp_path,
    terminal,
):

    terminal.rates = np.array([
        make_rate("2026-01-01T02:00:00Z"),
        make_rate("2026-01-01T02:01:00Z"),
        make_rate("2026-01-01T02:02:00Z"),
        make_rate("2026-01-01T02:03:00Z"),
    ], dtype=MT5_DTYPE)

    result = export_research_year(
        year=2026,
        output_folder=tmp_path,
        as_of_utc=datetime(
            2026, 1, 1, 0, 3, 37,
            tzinfo=UTC,
        ),
    )

    candles = pd.read_csv(
        result["csv_path"]
    )

    assert len(candles) == 3

    assert result["m1_export_path"] is None
    assert result["csv_path"].parent.name == "quarantine"

    assert pd.Timestamp(
        candles.iloc[-1]["datetime"]
    ) == pd.Timestamp(
        "2026-01-01T00:02:00Z"
    )

    metadata = read_json(
        result["metadata_path"]
    )

    assert metadata["requested_end_utc_exclusive"] == (
        "2026-01-01T00:03:00+00:00"
    )


def test_conflict_across_chunk_boundary(
    tmp_path,
    terminal,
):

    terminal.rates = np.array([
        make_rate("2025-02-01T02:00:00Z"),
    ], dtype=MT5_DTYPE)

    def conflicting_response(*args):

        rows = terminal.copy_rates(*args)

        if (
            args[2] == datetime(
                2025, 2, 1, 2, 0,
                tzinfo=UTC,
            )
        ):
            rows["close"] += 1

        return rows

    terminal.fetch.side_effect = (
        conflicting_response
    )

    with pytest.raises(
        mt5_fetcher.CandleConflictError
    ):

        export_research_year(
            year=2025,
            output_folder=tmp_path,
            as_of_utc=AS_OF,
        )

    folder = tmp_path / "2025"

    assert not list(folder.glob("*.csv"))

    conflicts = pd.read_csv(
        folder
        / "diagnostics"
        / "conflicting_candles.csv"
    )

    assert len(conflicts) == 2
    assert conflicts["datetime"].nunique() == 1
    assert conflicts["close"].nunique() == 2

    diagnostics = read_json(
        folder
        / "diagnostics"
        / "diagnostics.json"
    )

    assert diagnostics["duplicate_diagnostics"][
        "conflicting_timestamps"
    ] == 1

    terminal.shutdown.assert_called_once()


def test_native_mt5_failure_retains_diagnostics(
    tmp_path,
    terminal,
):

    terminal.fetch.side_effect = None
    terminal.fetch.return_value = None

    with pytest.raises(RuntimeError):

        export_research_year(
            year=2025,
            output_folder=tmp_path,
            as_of_utc=AS_OF,
        )

    folder = tmp_path / "2025"

    assert not list(folder.glob("*.csv"))

    diagnostics = read_json(
        folder
        / "diagnostics"
        / "diagnostics.json"
    )

    assert diagnostics["failure"][
        "stage"
    ] == "fetch"

    assert diagnostics["chunk_diagnostics"][0][
        "status"
    ] == "failed"

    assert diagnostics["chunk_diagnostics"][0][
        "mt5_error"
    ][0] == -1

    assert "987654321" not in json.dumps(
        diagnostics
    )

    terminal.shutdown.assert_called_once()


def test_empty_native_history(
    tmp_path,
    terminal,
):

    result = export_research_year(
        year=2025,
        output_folder=tmp_path,
        as_of_utc=AS_OF,
    )

    candles = pd.read_csv(
        result["csv_path"]
    )

    assert candles.empty
    assert "mt5_time_raw" in candles.columns

    assert result["m1_export_path"] is None
    assert result["csv_path"].parent.name == "quarantine"

    assert result["timeframe_decision"]["status"] == (
        "no_observations"
    )

    terminal.initialize.assert_called_once()
    terminal.shutdown.assert_called_once()

    metadata = read_json(
        result["metadata_path"]
    )

    assert metadata["data_status"] == (
        "no_observations"
    )

    assert metadata["rows_exported"] == 0

    assert metadata["coverage_summary"][
        "unobserved_minutes"
    ] == 525600

    assert verify_research_checksum(
        result["csv_path"]
    )


def test_ambiguous_native_timestamp_blocks_export(
    tmp_path,
    terminal,
):

    terminal.rates = np.array([
        make_rate("2025-11-02T08:30:00Z"),
    ], dtype=MT5_DTYPE)

    with pytest.raises(Exception):

        export_research_year(
            year=2025,
            output_folder=tmp_path,
            as_of_utc=AS_OF,
        )

    folder = tmp_path / "2025"

    assert not list(folder.glob("*.csv"))

    diagnostics = read_json(
        folder
        / "diagnostics"
        / "diagnostics.json"
    )

    assert any(
        record["status"] == "conversion_failed"
        for record in diagnostics["chunk_diagnostics"]
    )

    terminal.shutdown.assert_called_once()
