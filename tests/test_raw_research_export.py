import pandas as pd
import pytest

from src import exports


def make_candles():
    timestamps = pd.to_datetime(
        [
            "2025-01-15T02:30:00Z",
            "2025-01-15T14:30:00Z",
            "2025-01-15T14:32:00Z",
        ],
        utc=True,
    )

    return pd.DataFrame({
        "datetime": timestamps,
        "mt5_time_raw": [
            int(t.timestamp()) for t in timestamps
        ],
        "open": [
            20000.123456789013,
            20003.25,
            20005.25,
        ],
        "high": [20010.75, 20012.75, 20015.75],
        "low": [19998.50, 20000.50, 20002.50],
        "close": [20003.25, 20005.25, 20008.25],
        "tick_volume": [100, 0, 120],
        "spread": [15, 17, 20],
        "real_volume": [0, 0, 0],
    })


def test_raw_export_preserves_observations(tmp_path):
    candles = make_candles()

    output = exports.save_raw_research_csv(
        df=candles,
        output_folder=tmp_path,
        filename="research.csv",
    )

    loaded = pd.read_csv(
        output,
        float_precision="round_trip",
    )

    loaded["datetime"] = pd.to_datetime(
        loaded["datetime"],
        utc=True,
    )

    pd.testing.assert_frame_equal(
        loaded,
        candles,
        check_exact=True,
    )


def test_raw_export_does_not_modify_input(tmp_path):
    candles = make_candles()
    original = candles.copy(deep=True)

    exports.save_raw_research_csv(
        df=candles,
        output_folder=tmp_path,
        filename="research.csv",
    )

    pd.testing.assert_frame_equal(
        candles,
        original,
        check_exact=True,
    )


def test_raw_export_prevents_overwrite(tmp_path):
    existing = tmp_path / "research.csv"

    existing.write_text(
        "original historical data",
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError):
        exports.save_raw_research_csv(
            df=make_candles(),
            output_folder=tmp_path,
            filename="research.csv",
        )

    assert existing.read_text(
        encoding="utf-8"
    ) == "original historical data"


def test_raw_export_missing_columns_rejected(tmp_path):
    candles = make_candles().drop(
        columns=["spread"]
    )

    with pytest.raises(ValueError, match="spread"):
        exports.save_raw_research_csv(
            df=candles,
            output_folder=tmp_path,
            filename="research.csv",
        )

    assert not (tmp_path / "research.csv").exists()


def test_configurable_output_directory(tmp_path):
    folder = tmp_path / "historical" / "research"

    output = exports.save_raw_research_csv(
        df=make_candles(),
        output_folder=folder,
        filename="research.csv",
    )

    assert output == folder / "research.csv"
    assert output.exists()


def test_empty_export_preserves_schema(tmp_path):
    candles = make_candles().iloc[0:0]

    output = exports.save_raw_research_csv(
        df=candles,
        output_folder=tmp_path,
        filename="research.csv",
    )

    loaded = pd.read_csv(output)

    assert loaded.empty
    assert loaded.columns.tolist() == (
        candles.columns.tolist()
    )
