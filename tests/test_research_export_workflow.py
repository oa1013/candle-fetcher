import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from src import research_export
from src import mt5_fetcher
from src.exports import verify_research_checksum


UTC = timezone.utc

AS_OF = datetime(
    2026, 11, 26, 22, 15, 37,
    tzinfo=UTC,
)

CSV_NAME = "US100.cash_M1_2025.csv"
METADATA_NAME = "US100.cash_M1_2025.metadata.json"

QUARANTINE_CSV_NAME = (
    "US100.cash_M1_requested_2025.csv"
)

QUARANTINE_METADATA_NAME = (
    "US100.cash_M1_requested_2025.metadata.json"
)


@pytest.fixture
def connection(monkeypatch):

    initialize = Mock()
    shutdown = Mock()

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

    candles = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-01-15T14:30:00Z",
            "2025-07-15T14:30:00Z",
        ], utc=True),

        "mt5_time_raw": [
            int(pd.Timestamp(
                "2025-01-15T16:30:00Z"
            ).timestamp()),

            int(pd.Timestamp(
                "2025-07-15T17:30:00Z"
            ).timestamp()),
        ],

        "open": [20000.25, 21000.50],
        "high": [20010.75, 21015.25],
        "low": [19998.50, 20998.75],
        "close": [20003.25, 21010.50],
        "tick_volume": [100, 0],
        "spread": [15, 16],
        "real_volume": [0, 0],
    })

    state = SimpleNamespace(
        candles=candles,
        initialize=initialize,
        shutdown=shutdown,
    )

    def fake_fetch(**kwargs):

        if kwargs["timeframe_mt5"] == (
            mt5_fetcher.mt5.TIMEFRAME_H1
        ):

            kwargs["diagnostics"].append({
                "status": "empty",
                "rows_returned": 0,
                "mt5_error": None,
            })

            return mt5_fetcher.empty_candle_dataframe()

        assert kwargs["timeframe_mt5"] == (
            mt5_fetcher.mt5.TIMEFRAME_M1
        )

        kwargs["diagnostics"].append({
            "status": (
                "empty"
                if state.candles.empty
                else "returned"
            ),
            "rows_returned": len(state.candles),
            "mt5_error": None,
        })

        return state.candles.copy(deep=True)

    state.fetch = Mock(
        side_effect=fake_fetch
    )

    monkeypatch.setattr(
        mt5_fetcher,
        "fetch_candles_by_range",
        state.fetch,
    )

    return state


def run_export(folder):

    return research_export.export_research_year(
        year=2025,
        output_folder=folder,
        as_of_utc=AS_OF,
    )


def read_json(path):

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def test_complete_annual_export(
    tmp_path,
    connection,
):

    original = connection.candles.copy(deep=True)

    result = run_export(tmp_path)

    annual_folder = tmp_path / "2025"
    folder = annual_folder / "quarantine"

    csv_path = folder / QUARANTINE_CSV_NAME

    assert csv_path.is_file()

    assert (
        folder / QUARANTINE_METADATA_NAME
    ).is_file()

    assert result["m1_export_path"] is None
    assert result["quarantine_path"] == csv_path

    assert not (annual_folder / CSV_NAME).exists()
    assert not (annual_folder / METADATA_NAME).exists()

    assert result["timeframe_decision"]["status"] == (
        "review_required"
    )

    restored = pd.read_csv(
        csv_path,
        float_precision="round_trip",
    )

    restored["datetime"] = pd.to_datetime(
        restored["datetime"],
        utc=True,
    )

    pd.testing.assert_frame_equal(
        restored,
        original,
        check_exact=True,
    )

    assert verify_research_checksum(csv_path)

    assert connection.initialize.call_count == 2
    assert connection.shutdown.call_count == 2

    pd.testing.assert_frame_equal(
        connection.candles,
        original,
        check_exact=True,
    )


def test_metadata_contains_research_provenance(
    tmp_path,
    connection,
):

    run_export(tmp_path)

    metadata = read_json(
        tmp_path
        / "2025"
        / "quarantine"
        / QUARANTINE_METADATA_NAME
    )

    assert metadata["symbol"] == "US100.cash"
    assert metadata["requested_timeframe"] == "M1"
    assert metadata["timeframe"] == "unverified"
    assert metadata["quarantined"] is True
    assert metadata["server"] == "FTMO-Server3"

    assert metadata["broker"] == (
        "FTMO Global Markets Ltd"
    )

    assert metadata["year"] == 2025
    assert metadata["rows_exported"] == 2
    assert metadata["data_status"] == "review_required"

    assert "missing_h1_reference" in (
        metadata["timeframe_decision"]["blocking_reasons"]
    )

    assert metadata["native_m1_proven"] is False

    assert metadata["timestamp_mode"] == "ftmo_server"
    assert metadata["session_filter"] is None

    assert metadata["requested_start_utc"] == (
        "2025-01-01T00:00:00+00:00"
    )

    assert metadata["requested_end_utc_exclusive"] == (
        "2026-01-01T00:00:00+00:00"
    )

    assert metadata["coverage_summary"][
        "expected_trading_minutes"
    ] is None

    assert metadata["timestamp_validation"][
        "is_consistent"
    ] is True

    assert metadata["data_quality"][
        "zero_tick_volume_rows"
    ] == 1

    assert metadata["data_quality"][
        "zero_real_volume_rows"
    ] == 2

    assert "extracted_at_utc" in metadata
    assert "mt5_package_version" in metadata
    assert "git_commit" in metadata
    assert "sha256" in metadata

    assert "987654321" not in json.dumps(metadata)
    assert "login" not in metadata
    assert "password" not in metadata


def test_permanent_coverage_reports(
    tmp_path,
    connection,
):

    run_export(tmp_path)

    diagnostics = (
        tmp_path / "2025" / "diagnostics"
    )

    daily = pd.read_csv(
        diagnostics / "daily_coverage.csv"
    )

    monthly = pd.read_csv(
        diagnostics / "monthly_coverage.csv"
    )

    gaps = pd.read_csv(
        diagnostics / "historical_gaps.csv"
    )

    assert len(daily) == 365
    assert len(monthly) == 12

    assert daily["recorded_candles"].sum() == 2
    assert monthly["recorded_candles"].sum() == 2

    assert gaps["unobserved_minutes"].sum() == (
        525600 - 2
    )

    payload = read_json(
        diagnostics / "diagnostics.json"
    )

    assert payload["failure"] is None

    assert payload["chunk_diagnostics"][0][
        "status"
    ] == "returned"


def test_empty_history_explicitly_reported(
    tmp_path,
    connection,
):

    connection.candles = (
        connection.candles.iloc[:0].copy()
    )

    result = run_export(tmp_path)

    annual_folder = tmp_path / "2025"
    folder = annual_folder / "quarantine"

    csv_path = folder / QUARANTINE_CSV_NAME

    restored = pd.read_csv(csv_path)

    assert restored.empty
    assert verify_research_checksum(csv_path)

    assert result["m1_export_path"] is None
    assert not (annual_folder / CSV_NAME).exists()

    assert result["timeframe_decision"]["status"] == (
        "no_observations"
    )

    metadata = read_json(
        folder / QUARANTINE_METADATA_NAME
    )

    connection.initialize.assert_called_once()
    connection.shutdown.assert_called_once()

    assert metadata["rows_exported"] == 0
    assert metadata["data_status"] == "no_observations"

    assert metadata["coverage_summary"][
        "unobserved_minutes"
    ] == 525600


@pytest.mark.parametrize(
    "problem",
    [
        "timestamp_mismatch",
        "invalid_ohlc",
    ],
)
def test_invalid_dataset_blocks_export(
    tmp_path,
    connection,
    problem,
):

    if problem == "timestamp_mismatch":

        connection.candles.loc[
            0, "datetime"
        ] += pd.Timedelta(hours=1)

    elif problem == "invalid_ohlc":

        connection.candles.loc[
            0, "high"
        ] = 19000.0

    with pytest.raises(ValueError):
        run_export(tmp_path)

    folder = tmp_path / "2025"

    assert not (folder / CSV_NAME).exists()

    assert not list(
        (folder / "quarantine").glob("*.csv")
    )

    assert not (
        folder / METADATA_NAME
    ).exists()

    payload = read_json(
        folder
        / "diagnostics"
        / "diagnostics.json"
    )

    assert payload["failure"] is not None

    connection.shutdown.assert_called_once()


def test_fetch_failure_diagnostics_retained(
    tmp_path,
    connection,
):

    def failed_fetch(**kwargs):

        kwargs["diagnostics"].append({
            "status": "failed",
            "rows_returned": 0,
            "mt5_error": [
                -1,
                "Private account information 987654321",
            ],
        })

        raise RuntimeError(
            "Private account information 987654321"
        )

    connection.fetch.side_effect = failed_fetch

    with pytest.raises(RuntimeError):
        run_export(tmp_path)

    folder = tmp_path / "2025"

    assert not (folder / CSV_NAME).exists()

    assert not list(
        (folder / "quarantine").glob("*.csv")
    )

    payload = read_json(
        folder
        / "diagnostics"
        / "diagnostics.json"
    )

    assert payload["failure"][
        "error_type"
    ] == "RuntimeError"

    assert payload["chunk_diagnostics"][0][
        "status"
    ] == "failed"

    assert "987654321" not in json.dumps(payload)

    connection.shutdown.assert_called_once()


def test_conflict_evidence_saved(
    tmp_path,
    connection,
):

    first = connection.candles.iloc[[0]].copy()
    second = first.copy(deep=True)

    second["close"] = 20004.50

    conflicts = pd.concat(
        [first, second],
        ignore_index=True,
    )

    def conflict_fetch(**kwargs):

        kwargs["duplicate_diagnostics"][
            "conflicting_timestamps"
        ] = 1

        raise mt5_fetcher.CandleConflictError(
            conflicts
        )

    connection.fetch.side_effect = conflict_fetch

    with pytest.raises(
        mt5_fetcher.CandleConflictError
    ):
        run_export(tmp_path)

    folder = tmp_path / "2025"

    assert not (folder / CSV_NAME).exists()

    assert not list(
        (folder / "quarantine").glob("*.csv")
    )

    restored = pd.read_csv(
        folder
        / "diagnostics"
        / "conflicting_candles.csv",
        float_precision="round_trip",
    )

    restored["datetime"] = pd.to_datetime(
        restored["datetime"],
        utc=True,
    )

    pd.testing.assert_frame_equal(
        restored,
        conflicts,
        check_exact=True,
    )


def test_existing_year_never_overwritten(
    tmp_path,
    connection,
):

    result = run_export(tmp_path)

    csv_path = result["quarantine_path"]
    metadata_path = result["metadata_path"]

    original = csv_path.read_bytes()
    original_metadata = metadata_path.read_bytes()

    with pytest.raises(FileExistsError):
        run_export(tmp_path)

    assert csv_path.read_bytes() == original
    assert metadata_path.read_bytes() == original_metadata

    assert verify_research_checksum(csv_path)

    assert connection.initialize.call_count == 2
    assert connection.shutdown.call_count == 2
