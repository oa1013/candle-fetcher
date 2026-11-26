"""Dedicated native M1 historical research export engine."""

from __future__ import annotations

from datetime import datetime, timezone


UTC = timezone.utc


def get_research_year_bounds(
    year: int,
    as_of_utc: datetime,
) -> tuple[datetime, datetime]:
    """
    Return the UTC boundaries of a historical calendar year.

    The start boundary is inclusive.
    The end boundary is exclusive.

    For the current year, exclude the currently forming
    M1 candle by flooring the extraction time to a minute.
    """

    if (
        not isinstance(year, int)
        or isinstance(year, bool)
        or not 1 <= year <= 9998
    ):
        raise ValueError("Invalid calendar year.")

    if not isinstance(as_of_utc, datetime):
        raise ValueError("Extraction time must be a datetime.")

    if (
        as_of_utc.tzinfo is None
        or as_of_utc.utcoffset() is None
    ):
        raise ValueError(
            "Extraction time must be timezone-aware."
        )

    as_of_utc = as_of_utc.astimezone(UTC)

    if year > as_of_utc.year:
        raise ValueError(
            "Cannot extract a future calendar year."
        )

    start_utc = datetime(
        year, 1, 1, tzinfo=UTC
    )

    calendar_end_utc = datetime(
        year + 1, 1, 1, tzinfo=UTC
    )

    completed_candle_cutoff = as_of_utc.replace(
        second=0,
        microsecond=0,
    )

    end_utc_exclusive = min(
        calendar_end_utc,
        completed_candle_cutoff,
    )

    return start_utc, end_utc_exclusive
