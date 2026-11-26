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
    2026, 11, 26, 23, 0,
    tzinfo=UTC,
)

YEAR = 2025

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


def make_minute_rates():

    times = pd.date_range(
        "2025-01-02T02:00:00Z",
        periods=180,
        freq="min",
    )

    rows = []

    for i, timestamp in enumerate(times):

        price = 20000.0 + i

        rows.append((
            int(timestamp.timestamp()),
            price,
            price + 2,
            price - 1,
            price + 0.5,
            100,
            15,
            0,
        ))

    return np.array(
        rows,
        dtype=MT5_DTYPE,
    )


def make_hourly_rates():

    times = pd.date_range(
        "2025-01-02T02:00:00Z",
        periods=3,
        freq="h",
    )

    rows = []

    for i, timestamp in enumerate(times):

        price = 20000.0 + i * 60

        rows.append((
            int(timestamp.timestamp()),
            price,
            price + 61,
            price - 1,
            price + 59.5,
            6000,
            15,
            0,
        ))

    return np.array(
        rows,
        dtype=MT5_DTYPE,
    )


def read_json(path):

    return json.loads(
        path.read_text(encoding="utf-8")
    )


@pytest.fixture
def terminal(monkeypatch):

    state = SimpleNamespace(
        m1=make_minute_rates(),
        h1=make_hourly_rates(),
        fail_h1=False,
        initialize=Mock(return_value=True),
        shutdown=Mock(return_value=True),
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "initialize",
        state.initialize,
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "shutdown",
        state.shutdown,
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

    def copy_rates(symbol, timeframe, start, end):

        assert symbol == "US100.cash"

        if timeframe == mt5_fetcher.mt5.TIMEFRAME_M1:

            rates = state.m1

        elif timeframe == mt5_fetcher.mt5.TIMEFRAME_H1:

            if state.fail_h1:
                return None

            rates = state.h1

        else:

            raise AssertionError(
                "Unexpected requested timeframe."
            )

        mask = (
            (rates["time"] >= int(start.timestamp()))
            & (rates["time"] <= int(end.timestamp()))
        )

        return rates[mask].copy()

    state.fetch = Mock(
        side_effect=copy_rates
    )

    monkeypatch.setattr(
        mt5_fetcher.mt5,
        "copy_rates_range",
        state.fetch,
    )

    return state


def extract(tmp_path):

    return export_research_year(
        year=YEAR,
        output_folder=tmp_path,
        as_of_utc=AS_OF,
        chunk_days=31,
    )


def assert_preserved(path, original):

    actual = pd.read_csv(
        path,
        float_precision="round_trip",
    )

    assert len(actual) == len(original)

    assert actual["mt5_time_raw"].tolist() == (
        original["time"].tolist()
    )

    for field in MT5_DTYPE.names:

        if field == "time":
            continue

        assert actual[field].tolist() == (
            original[field].tolist()
        )

    assert verify_research_checksum(path)


def test_verified_minute_export(
    tmp_path,
    terminal,
):

    original = terminal.m1.copy()

    result = extract(tmp_path)

    assert result["m1_export_path"] == (
        tmp_path / "2025" / "US100.cash_M1_2025.csv"
    )

    assert result["csv_path"] == (
        result["m1_export_path"]
    )

    assert result["timeframe_decision"][
        "allow_m1_export"
    ] is True

    assert result["rows_exported"] == 180

    assert_preserved(
        result["csv_path"],
        original,
    )

    metadata = read_json(
        result["metadata_path"]
    )

    assert metadata["timeframe"] == "M1"
    assert metadata["requested_timeframe"] == "M1"

    assert metadata["timeframe_decision"][
        "status"
    ] == "minute_level_supported"

    assert metadata[
        "historical_completeness_verified"
    ] is False

    diagnostics = read_json(
        result["diagnostics_path"]
    )

    assert diagnostics["timeframe_verification"][
        "aggregation_comparison"
    ]["exact_matches"] == 3

    assert diagnostics["h1_reference"][
        "rows_fetched"
    ] == 3

    assert terminal.initialize.call_count == 2
    assert terminal.shutdown.call_count == 2


def test_mixed_timeframe_quarantined(
    tmp_path,
    terminal,
):

    hourly = make_hourly_rates().copy()

    hourly["time"] -= 86400

    terminal.m1 = np.concatenate([
        hourly,
        terminal.m1,
    ])

    terminal.h1 = np.concatenate([
        hourly,
        terminal.h1,
    ])

    original = terminal.m1.copy()

    result = extract(tmp_path)

    assert result["m1_export_path"] is None

    assert result["csv_path"].parent.name == (
        "quarantine"
    )

    assert not (
        tmp_path / "2025" / "US100.cash_M1_2025.csv"
    ).exists()

    assert result["timeframe_decision"][
        "status"
    ] == "review_required"

    assert "exact_direct_h1_matches" in (
        result["timeframe_decision"][
            "blocking_reasons"
        ]
    )

    assert_preserved(
        result["csv_path"],
        original,
    )

    metadata = read_json(
        result["metadata_path"]
    )

    assert metadata["timeframe"] == "unverified"

    assert metadata["requested_timeframe"] == "M1"

    assert metadata["data_status"] == "review_required"

    assert metadata["rows_exported"] == 183


def test_missing_h1_reference_quarantined(
    tmp_path,
    terminal,
):

    terminal.h1 = np.array(
        [],
        dtype=MT5_DTYPE,
    )

    result = extract(tmp_path)

    assert result["m1_export_path"] is None

    assert "missing_h1_reference" in (
        result["timeframe_decision"][
            "blocking_reasons"
        ]
    )

    assert_preserved(
        result["csv_path"],
        terminal.m1,
    )


def test_aggregation_discrepancy_quarantined(
    tmp_path,
    terminal,
):

    terminal.h1["high"][0] += 5

    result = extract(tmp_path)

    assert result["m1_export_path"] is None

    assert "aggregation_mismatches" in (
        result["timeframe_decision"][
            "blocking_reasons"
        ]
    )

    assert_preserved(
        result["csv_path"],
        terminal.m1,
    )


def test_h1_failure_preserves_m1_evidence(
    tmp_path,
    terminal,
):

    terminal.fail_h1 = True

    result = extract(tmp_path)

    assert result["m1_export_path"] is None

    assert "h1_reference_fetch_failed" in (
        result["timeframe_decision"][
            "blocking_reasons"
        ]
    )

    assert_preserved(
        result["csv_path"],
        terminal.m1,
    )

    diagnostics = read_json(
        result["diagnostics_path"]
    )

    assert "987654321" not in json.dumps(
        diagnostics
    )

    assert terminal.shutdown.call_count == 2


def test_empty_history_not_published_as_m1(
    tmp_path,
    terminal,
):

    terminal.m1 = np.array(
        [],
        dtype=MT5_DTYPE,
    )

    result = extract(tmp_path)

    assert result["m1_export_path"] is None

    assert result["timeframe_decision"][
        "status"
    ] == "no_observations"

    assert result["rows_exported"] == 0

    metadata = read_json(
        result["metadata_path"]
    )

    assert metadata["data_status"] == (
        "no_observations"
    )

    assert_preserved(
        result["csv_path"],
        terminal.m1,
    )
