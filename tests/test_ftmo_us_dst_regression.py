"""Regression tests for the observed FTMO-Server3 clock convention.

The FTMO server wall clock is seven hours ahead of New York
wall time for the verified 2024 historical sessions.

These tests must not require a live MT5 connection.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from src.ftmo_time import (
    ftmo_raw_seconds_to_utc,
    utc_to_ftmo_request_clock,
)


UTC = timezone.utc
NY = ZoneInfo("America/New_York")

REFERENCE_DATES = (
    "2024-03-06",
    "2024-03-13",
    "2024-04-03",
    "2024-10-23",
    "2024-10-30",
    "2024-11-06",
)


def expected_cash_open_utc(day):
    local = datetime.fromisoformat(
        f"{day}T09:30:00"
    ).replace(tzinfo=NY)

    return local.astimezone(UTC)


def test_cash_open_request_clock_is_1630():
    """NY 09:30 must map to FTMO server 16:30."""

    failures = []

    for day in REFERENCE_DATES:
        actual_utc = expected_cash_open_utc(day)

        encoded = utc_to_ftmo_request_clock(
            actual_utc
        )

        if encoded.strftime("%H:%M") != "16:30":
            failures.append(
                f"{day}: got {encoded:%H:%M}"
            )

    assert not failures, (
        "Incorrect FTMO request clock:\n"
        + "\n".join(failures)
    )


def test_server_1630_decodes_to_ny_cash_open():
    """Known server-clock labels must decode to real UTC."""

    failures = []

    for day in REFERENCE_DATES:
        server_label = pd.Timestamp(
            f"{day}T16:30:00Z"
        )

        recovered = ftmo_raw_seconds_to_utc(
            pd.Series([
                int(server_label.timestamp())
            ])
        ).iloc[0]

        expected = pd.Timestamp(
            expected_cash_open_utc(day)
        )

        if recovered != expected:
            failures.append(
                f"{day}: received {recovered}, "
                f"expected {expected}"
            )

    assert not failures, (
        "Incorrect FTMO timestamp decoding:\n"
        + "\n".join(failures)
    )


def test_us_dst_invalid_wall_times_rejected():
    """Reject nonexistent and ambiguous NY-derived times."""

    # US spring-forward: NY 02:30 does not exist.
    # FTMO server wall time = NY wall time + 7h.
    nonexistent = pd.Timestamp(
        "2024-03-10T09:30:00Z"
    )

    # US autumn fallback: NY 01:30 is ambiguous.
    ambiguous = pd.Timestamp(
        "2024-11-03T08:30:00Z"
    )

    for raw_label in (nonexistent, ambiguous):
        with pytest.raises(Exception):
            ftmo_raw_seconds_to_utc(
                pd.Series([
                    int(raw_label.timestamp())
                ])
            )
