from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd


DateLike = str | date | datetime | None


# ---------------------------------------------------------------------------
# Datetime helpers
# ---------------------------------------------------------------------------

def parse_date(value: DateLike) -> date | None:
    """
    Parse a date-like value into a Python date.

    Supports:
        "2021-01-01"
        "2021/01/01"
        date objects
        datetime objects
        None
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    parsed = pd.to_datetime(value, errors="raise")
    return parsed.date()


def get_datetime_series(
    df: pd.DataFrame,
    datetime_column: str = "datetime",
    timezone_name: str = "UTC",
) -> pd.Series:
    """
    Return a timezone-aware datetime Series converted to the requested timezone.

    If the datetime column is timezone-naive, it is treated as UTC.
    """
    if datetime_column not in df.columns:
        raise ValueError(f"Missing datetime column: {datetime_column}")

    utc_series = pd.to_datetime(df[datetime_column], utc=True, errors="coerce")
    return utc_series.dt.tz_convert(ZoneInfo(timezone_name))


def normalize_to_list(value) -> list:
    """Convert a single value or iterable into a list."""
    if value is None:
        return []

    if isinstance(value, (str, int)):
        return [value]

    return list(value)


# ---------------------------------------------------------------------------
# Date range filters
# ---------------------------------------------------------------------------

def filter_by_date_range(
    df: pd.DataFrame,
    start_date: DateLike = None,
    end_date: DateLike = None,
    datetime_column: str = "datetime",
    timezone_name: str = "UTC",
) -> pd.DataFrame:
    """
    Filter candles by an inclusive date range.

    Examples:
        filter_by_date_range(df, "2021-01-01", "2021-12-31")
        filter_by_date_range(df, "2023/12/03", "2024/12/03")
    """
    if df.empty:
        return df.copy()

    start_day = parse_date(start_date)
    end_day = parse_date(end_date)

    local_dt = get_datetime_series(
        df=df,
        datetime_column=datetime_column,
        timezone_name=timezone_name,
    )

    mask = pd.Series(True, index=df.index)

    if start_day is not None:
        start_local = datetime.combine(
            start_day,
            time.min,
            tzinfo=ZoneInfo(timezone_name),
        )
        mask &= local_dt >= start_local

    if end_day is not None:
        end_exclusive_local = datetime.combine(
            end_day + timedelta(days=1),
            time.min,
            tzinfo=ZoneInfo(timezone_name),
        )
        mask &= local_dt < end_exclusive_local

    return df.loc[mask].reset_index(drop=True)


def filter_by_year_range(
    df: pd.DataFrame,
    start_year: int,
    end_year: int,
    datetime_column: str = "datetime",
    timezone_name: str = "UTC",
) -> pd.DataFrame:
    """
    Filter candles by an inclusive year range.

    Example:
        filter_by_year_range(df, 2000, 2010)
    """
    if end_year < start_year:
        raise ValueError("end_year cannot be before start_year.")

    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"

    return filter_by_date_range(
        df=df,
        start_date=start_date,
        end_date=end_date,
        datetime_column=datetime_column,
        timezone_name=timezone_name,
    )


def filter_by_years(
    df: pd.DataFrame,
    years: int | Iterable[int],
    datetime_column: str = "datetime",
    timezone_name: str = "UTC",
) -> pd.DataFrame:
    """
    Filter candles by one or more years.

    Examples:
        filter_by_years(df, 2021)
        filter_by_years(df, [2021, 2022, 2023])
    """
    years = [int(year) for year in normalize_to_list(years)]

    local_dt = get_datetime_series(
        df=df,
        datetime_column=datetime_column,
        timezone_name=timezone_name,
    )

    mask = local_dt.dt.year.isin(years)
    return df.loc[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Calendar component filters
# ---------------------------------------------------------------------------

def filter_by_months(
    df: pd.DataFrame,
    months: int | Iterable[int],
    datetime_column: str = "datetime",
    timezone_name: str = "UTC",
) -> pd.DataFrame:
    """
    Filter candles by one or more months.

    Examples:
        filter_by_months(df, 1)
        filter_by_months(df, [1, 2, 3])
    """
    months = [int(month) for month in normalize_to_list(months)]

    for month in months:
        if month < 1 or month > 12:
            raise ValueError("months must be between 1 and 12.")

    local_dt = get_datetime_series(
        df=df,
        datetime_column=datetime_column,
        timezone_name=timezone_name,
    )

    mask = local_dt.dt.month.isin(months)
    return df.loc[mask].reset_index(drop=True)


def filter_by_iso_weeks(
    df: pd.DataFrame,
    weeks: int | Iterable[int],
    datetime_column: str = "datetime",
    timezone_name: str = "UTC",
) -> pd.DataFrame:
    """
    Filter candles by one or more ISO week numbers.

    Examples:
        filter_by_iso_weeks(df, 1)
        filter_by_iso_weeks(df, [1, 2, 3])
    """
    weeks = [int(week) for week in normalize_to_list(weeks)]

    for week in weeks:
        if week < 1 or week > 53:
            raise ValueError("weeks must be between 1 and 53.")

    local_dt = get_datetime_series(
        df=df,
        datetime_column=datetime_column,
        timezone_name=timezone_name,
    )

    iso_calendar = local_dt.dt.isocalendar()
    mask = iso_calendar.week.isin(weeks)

    return df.loc[mask].reset_index(drop=True)


def filter_by_days(
    df: pd.DataFrame,
    days: DateLike | Iterable[DateLike],
    datetime_column: str = "datetime",
    timezone_name: str = "UTC",
) -> pd.DataFrame:
    """
    Filter candles by one or more exact calendar days.

    Examples:
        filter_by_days(df, "2023-12-03")
        filter_by_days(df, ["2023-12-03", "2023-12-04"])
    """
    parsed_days = [
        parse_date(day)
        for day in normalize_to_list(days)
    ]

    local_dt = get_datetime_series(
        df=df,
        datetime_column=datetime_column,
        timezone_name=timezone_name,
    )

    local_dates = local_dt.dt.date
    mask = local_dates.isin(parsed_days)

    return df.loc[mask].reset_index(drop=True)


def filter_by_weekdays(
    df: pd.DataFrame,
    weekdays: int | str | Iterable[int | str],
    datetime_column: str = "datetime",
    timezone_name: str = "UTC",
) -> pd.DataFrame:
    """
    Filter candles by weekday.

    Accepts integers:
        Monday=0, Tuesday=1, ..., Sunday=6

    Or names:
        "monday", "tuesday", etc.
    """
    weekday_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    normalized_weekdays = []

    for weekday in normalize_to_list(weekdays):
        if isinstance(weekday, str):
            key = weekday.strip().lower()

            if key not in weekday_map:
                raise ValueError(
                    f"Invalid weekday '{weekday}'. Use monday, tuesday, etc."
                )

            normalized_weekdays.append(weekday_map[key])
        else:
            weekday_int = int(weekday)

            if weekday_int < 0 or weekday_int > 6:
                raise ValueError("weekday integers must be between 0 and 6.")

            normalized_weekdays.append(weekday_int)

    local_dt = get_datetime_series(
        df=df,
        datetime_column=datetime_column,
        timezone_name=timezone_name,
    )

    mask = local_dt.dt.weekday.isin(normalized_weekdays)
    return df.loc[mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Combined helper
# ---------------------------------------------------------------------------

def apply_date_filters(
    df: pd.DataFrame,
    start_date: DateLike = None,
    end_date: DateLike = None,
    years: int | Iterable[int] | None = None,
    months: int | Iterable[int] | None = None,
    weeks: int | Iterable[int] | None = None,
    days: DateLike | Iterable[DateLike] | None = None,
    weekdays: int | str | Iterable[int | str] | None = None,
    datetime_column: str = "datetime",
    timezone_name: str = "UTC",
) -> pd.DataFrame:
    """
    Apply multiple date filters in sequence.

    Any filter left as None is ignored.
    """
    filtered = df.copy()

    if start_date is not None or end_date is not None:
        filtered = filter_by_date_range(
            df=filtered,
            start_date=start_date,
            end_date=end_date,
            datetime_column=datetime_column,
            timezone_name=timezone_name,
        )

    if years is not None:
        filtered = filter_by_years(
            df=filtered,
            years=years,
            datetime_column=datetime_column,
            timezone_name=timezone_name,
        )

    if months is not None:
        filtered = filter_by_months(
            df=filtered,
            months=months,
            datetime_column=datetime_column,
            timezone_name=timezone_name,
        )

    if weeks is not None:
        filtered = filter_by_iso_weeks(
            df=filtered,
            weeks=weeks,
            datetime_column=datetime_column,
            timezone_name=timezone_name,
        )

    if days is not None:
        filtered = filter_by_days(
            df=filtered,
            days=days,
            datetime_column=datetime_column,
            timezone_name=timezone_name,
        )

    if weekdays is not None:
        filtered = filter_by_weekdays(
            df=filtered,
            weekdays=weekdays,
            datetime_column=datetime_column,
            timezone_name=timezone_name,
        )

    return filtered.reset_index(drop=True)