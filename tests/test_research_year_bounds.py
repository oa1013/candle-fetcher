from datetime import datetime, timedelta, timezone

import pytest

from src import research_export


UTC = timezone.utc


def test_completed_calendar_year():
    start, end = research_export.get_research_year_bounds(
        year=2025,
        as_of_utc=datetime(
            2026, 11, 26, 22, 15, tzinfo=UTC
        ),
    )

    assert start == datetime(2025, 1, 1, tzinfo=UTC)
    assert end == datetime(2026, 1, 1, tzinfo=UTC)


def test_leap_year():
    start, end = research_export.get_research_year_bounds(
        year=2024,
        as_of_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert (end - start).days == 366


def test_consecutive_years_do_not_overlap():
    as_of = datetime(2026, 11, 26, tzinfo=UTC)

    _, first_end = research_export.get_research_year_bounds(
        year=2024,
        as_of_utc=as_of,
    )

    second_start, _ = research_export.get_research_year_bounds(
        year=2025,
        as_of_utc=as_of,
    )

    assert first_end == second_start


def test_current_year_excludes_forming_candle():
    start, end = research_export.get_research_year_bounds(
        year=2026,
        as_of_utc=datetime(
            2026, 11, 26, 22, 15, 37, tzinfo=UTC
        ),
    )

    assert start == datetime(2026, 1, 1, tzinfo=UTC)

    assert end == datetime(
        2026, 11, 26, 22, 15, tzinfo=UTC
    )


def test_exact_minute_boundary():
    _, end = research_export.get_research_year_bounds(
        year=2026,
        as_of_utc=datetime(
            2026, 11, 26, 22, 15, tzinfo=UTC
        ),
    )

    assert end == datetime(
        2026, 11, 26, 22, 15, tzinfo=UTC
    )


def test_timezone_offset_normalized_to_utc():
    offset = timezone(timedelta(hours=3))

    _, end = research_export.get_research_year_bounds(
        year=2026,
        as_of_utc=datetime(
            2026, 11, 26, 22, 15, 37,
            tzinfo=offset,
        ),
    )

    assert end == datetime(
        2026, 11, 26, 19, 15, tzinfo=UTC
    )


def test_future_year_rejected():
    with pytest.raises(ValueError, match="(?i)future"):
        research_export.get_research_year_bounds(
            year=2027,
            as_of_utc=datetime(
                2026, 11, 26, tzinfo=UTC
            ),
        )


def test_naive_extraction_time_rejected():
    with pytest.raises(ValueError, match="(?i)timezone"):
        research_export.get_research_year_bounds(
            year=2025,
            as_of_utc=datetime(2026, 11, 26),
        )


def test_no_completed_candles_at_year_start():
    start, end = research_export.get_research_year_bounds(
        year=2026,
        as_of_utc=datetime(
            2026, 1, 1, 0, 0, 30, tzinfo=UTC
        ),
    )

    assert start == end


def test_microseconds_removed_from_cutoff():
    _, end = research_export.get_research_year_bounds(
        year=2026,
        as_of_utc=datetime(
            2026, 11, 26, 22, 15, 37, 123456,
            tzinfo=UTC,
        ),
    )

    assert end.second == 0
    assert end.microsecond == 0
