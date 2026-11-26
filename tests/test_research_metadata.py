import hashlib
import json

import pytest

from src import exports


def make_csv(tmp_path):
    path = tmp_path / "research.csv"

    path.write_bytes(
        b"datetime,open,close\n"
        b"2025-01-15T14:30:00Z,20000.25,20003.25\n"
    )

    return path


def make_metadata():
    return {
        "symbol": "US100.cash",
        "timeframe": "M1",
        "broker": "FTMO Global Markets Ltd",
        "server": "FTMO-Server3",
        "timestamp_mode": "ftmo_server",
        "requested_start_utc": "2025-01-01T00:00:00Z",
        "requested_end_utc_exclusive": "2026-01-01T00:00:00Z",
        "rows_saved": 1,
        "warnings": [],
    }


def test_sha256_matches_independent_calculation(tmp_path):
    path = make_csv(tmp_path)

    expected = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    assert exports.compute_file_sha256(path) == expected


def test_metadata_sidecar_created(tmp_path):
    path = make_csv(tmp_path)
    metadata = make_metadata()

    output = exports.save_research_metadata(
        csv_path=path,
        metadata=metadata,
    )

    assert output == path.with_suffix(".metadata.json")

    saved = json.loads(
        output.read_text(encoding="utf-8")
    )

    for key, value in metadata.items():
        assert saved[key] == value

    assert saved["csv_filename"] == path.name

    assert saved["sha256"] == hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_metadata_input_not_modified(tmp_path):
    path = make_csv(tmp_path)

    metadata = make_metadata()
    original = make_metadata()

    exports.save_research_metadata(
        csv_path=path,
        metadata=metadata,
    )

    assert metadata == original


def test_metadata_overwrite_prevented(tmp_path):
    path = make_csv(tmp_path)
    metadata = make_metadata()

    output = exports.save_research_metadata(
        csv_path=path,
        metadata=metadata,
    )

    original = output.read_bytes()

    metadata["rows_saved"] = 999

    with pytest.raises(FileExistsError):
        exports.save_research_metadata(
            csv_path=path,
            metadata=metadata,
        )

    assert output.read_bytes() == original


def test_valid_checksum_verified(tmp_path):
    path = make_csv(tmp_path)

    exports.save_research_metadata(
        csv_path=path,
        metadata=make_metadata(),
    )

    assert exports.verify_research_checksum(path) is True


def test_modified_csv_detected(tmp_path):
    path = make_csv(tmp_path)

    exports.save_research_metadata(
        csv_path=path,
        metadata=make_metadata(),
    )

    with path.open("ab") as file:
        file.write(b"modified data\n")

    assert exports.verify_research_checksum(path) is False


def test_missing_metadata_rejected(tmp_path):
    path = make_csv(tmp_path)

    with pytest.raises(FileNotFoundError):
        exports.verify_research_checksum(path)


def test_missing_csv_rejected(tmp_path):
    path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        exports.save_research_metadata(
            csv_path=path,
            metadata=make_metadata(),
        )

    assert not path.with_suffix(
        ".metadata.json"
    ).exists()


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
def test_required_provenance_fields(tmp_path, field):
    path = make_csv(tmp_path)
    metadata = make_metadata()

    del metadata[field]

    with pytest.raises(ValueError, match=field):
        exports.save_research_metadata(
            csv_path=path,
            metadata=metadata,
        )

    assert not path.with_suffix(
        ".metadata.json"
    ).exists()


def test_invalid_checksum_rejected(tmp_path):
    path = make_csv(tmp_path)

    output = exports.save_research_metadata(
        csv_path=path,
        metadata=make_metadata(),
    )

    metadata = json.loads(
        output.read_text(encoding="utf-8")
    )

    metadata["sha256"] = "invalid-checksum"

    output.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="(?i)sha256"):
        exports.verify_research_checksum(path)
