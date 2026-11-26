import json

import pandas as pd
import pytest

from src import exports
from src.data_quality import build_research_coverage_report


def make_candles():
    return pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-01-15T14:30:00Z",
            "2025-01-15T14:32:00Z",
        ], utc=True),
        "mt5_time_raw": [
            1736958600,
            1736958720,
        ],
        "open": [20000.25, 20005.50],
        "high": [20010.75, 20015.25],
        "low": [19998.50, 20001.75],
        "close": [20003.25, 20010.50],
        "tick_volume": [100, 150],
        "spread": [15, 16],
        "real_volume": [0, 0],
    })


def make_coverage():
    return build_research_coverage_report(
        make_candles(),
        start_utc=pd.Timestamp(
            "2025-01-15T14:30:00Z"
        ),
        end_utc_exclusive=pd.Timestamp(
            "2025-01-15T14:34:00Z"
        ),
    )


def make_chunks():
    return [
        {
            "status": "returned",
            "rows_returned": 2,
            "mt5_error": None,
        },
        {
            "status": "empty",
            "rows_returned": 0,
            "mt5_error": None,
        },
    ]


def make_duplicates():
    return {
        "identical_duplicates": 1,
        "conflicting_timestamps": 0,
    }


def save(folder, **kwargs):
    arguments = {
        "chunk_diagnostics": make_chunks(),
        "duplicate_diagnostics": make_duplicates(),
    }

    arguments.update(kwargs)

    return exports.save_research_diagnostics(
        output_folder=folder,
        **arguments,
    )


def test_chunk_diagnostics_saved(tmp_path):
    folder = tmp_path / "diagnostics"

    save(folder)

    payload = json.loads(
        (folder / "diagnostics.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload["chunk_diagnostics"] == make_chunks()

    assert payload["duplicate_diagnostics"] == (
        make_duplicates()
    )

    assert payload["diagnostics_schema_version"] == 1
    assert payload["failure"] is None


def test_coverage_reports_saved(tmp_path):
    folder = tmp_path / "diagnostics"

    coverage = make_coverage()

    save(
        folder,
        coverage=coverage,
    )

    assert (folder / "daily_coverage.csv").is_file()
    assert (folder / "monthly_coverage.csv").is_file()
    assert (folder / "historical_gaps.csv").is_file()

    daily = pd.read_csv(
        folder / "daily_coverage.csv"
    )

    monthly = pd.read_csv(
        folder / "monthly_coverage.csv"
    )

    gaps = pd.read_csv(
        folder / "historical_gaps.csv"
    )

    assert daily["recorded_candles"].sum() == 2
    assert monthly["recorded_candles"].sum() == 2
    assert gaps["unobserved_minutes"].sum() == 2

    payload = json.loads(
        (folder / "diagnostics.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload["coverage_summary"] == (
        coverage["summary"]
    )


def test_failure_diagnostics_saved(tmp_path):
    folder = tmp_path / "diagnostics"

    failure = {
        "error_type": "RuntimeError",
        "message": "Simulated MT5 extraction failure",
    }

    save(
        folder,
        failure=failure,
        chunk_diagnostics=[
            {
                "status": "failed",
                "rows_returned": 0,
                "mt5_error": [-1, "Simulated failure"],
            }
        ],
    )

    payload = json.loads(
        (folder / "diagnostics.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload["failure"] == failure

    assert payload["chunk_diagnostics"][0][
        "status"
    ] == "failed"

    assert payload["coverage_summary"] is None

    assert not (
        folder / "daily_coverage.csv"
    ).exists()


def test_conflicting_observations_preserved(tmp_path):
    folder = tmp_path / "diagnostics"

    first = make_candles().iloc[[0]].copy()
    second = first.copy(deep=True)

    second["close"] = 20004.50

    conflicts = pd.concat(
        [first, second],
        ignore_index=True,
    )

    original = conflicts.copy(deep=True)

    save(
        folder,
        conflicting_rows=conflicts,
        duplicate_diagnostics={
            "identical_duplicates": 0,
            "conflicting_timestamps": 1,
        },
        failure={
            "error_type": "CandleConflictError",
            "message": "Conflicting candle observations",
        },
    )

    restored = pd.read_csv(
        folder / "conflicting_candles.csv",
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

    pd.testing.assert_frame_equal(
        conflicts,
        original,
        check_exact=True,
    )


def test_existing_reports_never_overwritten(tmp_path):
    folder = tmp_path / "diagnostics"

    save(folder)

    report = folder / "diagnostics.json"
    original = report.read_bytes()

    with pytest.raises(FileExistsError):
        save(folder)

    assert report.read_bytes() == original


def test_optional_reports_not_fabricated(tmp_path):
    folder = tmp_path / "diagnostics"

    save(folder)

    assert not (
        folder / "daily_coverage.csv"
    ).exists()

    assert not (
        folder / "monthly_coverage.csv"
    ).exists()

    assert not (
        folder / "historical_gaps.csv"
    ).exists()

    assert not (
        folder / "conflicting_candles.csv"
    ).exists()


def test_invalid_json_does_not_create_report(tmp_path):
    folder = tmp_path / "diagnostics"

    with pytest.raises((ValueError, TypeError)):
        save(
            folder,
            chunk_diagnostics=[
                {"rows_returned": float("nan")}
            ],
        )

    assert not folder.exists()


def test_custom_nested_output_directory(tmp_path):
    folder = (
        tmp_path
        / "research"
        / "2025"
        / "diagnostics"
    )

    save(folder)

    assert (
        folder / "diagnostics.json"
    ).is_file()


def test_empty_coverage_reports_preserve_headers(tmp_path):
    folder = tmp_path / "diagnostics"

    coverage = build_research_coverage_report(
        make_candles().iloc[:0],
        start_utc=pd.Timestamp(
            "2025-01-01T00:00:00Z"
        ),
        end_utc_exclusive=pd.Timestamp(
            "2025-01-01T00:00:00Z"
        ),
    )

    save(
        folder,
        coverage=coverage,
    )

    daily = pd.read_csv(
        folder / "daily_coverage.csv"
    )

    gaps = pd.read_csv(
        folder / "historical_gaps.csv"
    )

    assert daily.empty
    assert gaps.empty

    assert "recorded_candles" in daily.columns
    assert "gap_type" in gaps.columns
