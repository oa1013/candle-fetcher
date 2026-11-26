import json

import pandas as pd
import pytest

from src.loaders import load_candle_folder


def make_dataset(
    folder,
    name,
    timestamp,
    metadata=True,
    **overrides,
):
    path = folder / f"{name}.csv"

    pd.DataFrame([
        {
            "datetime": timestamp,
            "open": 20000.25,
            "high": 20010.75,
            "low": 19998.50,
            "close": 20003.25,
            "tick_volume": 100,
            "spread": 15,
            "real_volume": 0,
        }
    ]).to_csv(path, index=False)

    if metadata:
        details = {
            "symbol": "US100.cash",
            "timeframe": "M1",
            "broker": "FTMO Global Markets Ltd",
            "server": "FTMO-Server3",
            "timestamp_mode": "ftmo_server",
        }

        details.update(overrides)

        path.with_suffix(".metadata.json").write_text(
            json.dumps(details),
            encoding="utf-8",
        )

    return path


def test_single_legacy_csv_remains_readable(tmp_path):
    make_dataset(
        tmp_path,
        "legacy",
        "2025-01-15T14:30:00Z",
        metadata=False,
    )

    result = load_candle_folder(tmp_path)

    assert len(result) == 1


def test_compatible_datasets_combined(tmp_path):
    make_dataset(
        tmp_path,
        "first",
        "2025-01-15T14:30:00Z",
    )

    make_dataset(
        tmp_path,
        "second",
        "2025-01-15T14:31:00Z",
    )

    result = load_candle_folder(tmp_path)

    assert len(result) == 2
    assert result["datetime"].is_monotonic_increasing


@pytest.mark.parametrize(
    "field, incompatible_value",
    [
        ("symbol", "US30.cash"),
        ("timeframe", "H1"),
        ("broker", "Other Broker"),
        ("server", "FTMO-Demo"),
        ("timestamp_mode", "utc"),
    ],
)
def test_incompatible_datasets_rejected(
    tmp_path,
    field,
    incompatible_value,
):
    make_dataset(
        tmp_path,
        "first",
        "2025-01-15T14:30:00Z",
    )

    make_dataset(
        tmp_path,
        "second",
        "2025-01-15T14:31:00Z",
        **{field: incompatible_value},
    )

    with pytest.raises(ValueError, match="(?i)incompatible"):
        load_candle_folder(tmp_path)


def test_unverified_multiple_datasets_rejected(tmp_path):
    make_dataset(
        tmp_path,
        "first",
        "2025-01-15T14:30:00Z",
        metadata=False,
    )

    make_dataset(
        tmp_path,
        "second",
        "2025-01-15T14:31:00Z",
        metadata=False,
    )

    with pytest.raises(ValueError, match="(?i)metadata"):
        load_candle_folder(tmp_path)


def test_missing_metadata_rejected(tmp_path):
    make_dataset(
        tmp_path,
        "first",
        "2025-01-15T14:30:00Z",
    )

    make_dataset(
        tmp_path,
        "second",
        "2025-01-15T14:31:00Z",
        metadata=False,
    )

    with pytest.raises(ValueError, match="(?i)metadata"):
        load_candle_folder(tmp_path)


def test_corrupted_metadata_rejected(tmp_path):
    path = make_dataset(
        tmp_path,
        "corrupted",
        "2025-01-15T14:30:00Z",
    )

    path.with_suffix(".metadata.json").write_text(
        "invalid JSON",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="(?i)metadata"):
        load_candle_folder(tmp_path)


@pytest.mark.parametrize(
    "field",
    [
        "symbol",
        "timeframe",
        "broker",
        "server",
        "timestamp_mode",
    ],
)
def test_required_metadata_fields(tmp_path, field):
    path = make_dataset(
        tmp_path,
        "incomplete",
        "2025-01-15T14:30:00Z",
    )

    metadata_path = path.with_suffix(".metadata.json")

    metadata = json.loads(
        metadata_path.read_text(encoding="utf-8")
    )

    del metadata[field]

    metadata_path.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="(?i)metadata"):
        load_candle_folder(tmp_path)


def test_invalid_metadata_structure(tmp_path):
    path = make_dataset(
        tmp_path,
        "invalid",
        "2025-01-15T14:30:00Z",
    )

    path.with_suffix(".metadata.json").write_text(
        json.dumps(["invalid", "structure"]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="(?i)metadata"):
        load_candle_folder(tmp_path)
