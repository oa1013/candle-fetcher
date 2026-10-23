import pandas as pd

from .session_filters import filter_by_session, get_session_config
from .data_quality import validate_session_coverage


def calculate_range(df: pd.DataFrame) -> dict:
    """
    Calculate the high, low, and price range
    for a collection of OHLC candles.
    """

    required_columns = {"high", "low"}

    if not required_columns.issubset(df.columns):
        raise ValueError("Candle data must contain high and low columns.")

    if df.empty:
        raise ValueError("Cannot calculate a range from empty candle data.")

    highest_price = float(df["high"].max())
    lowest_price = float(df["low"].min())

    if pd.isna(highest_price) or pd.isna(lowest_price):
        raise ValueError("Candle highs and lows must contain valid prices.")

    if lowest_price <= 0 or highest_price < lowest_price:
        raise ValueError("Invalid high or low prices.")

    range_points = highest_price - lowest_price
    range_percent = (range_points / lowest_price) * 100

    return {
        "high": highest_price,
        "low": lowest_price,
        "range_points": round(range_points, 2),
        "range_percent": round(range_percent, 4),
    }

def calculate_daily_ranges(
    df: pd.DataFrame,
    timezone: str = "UTC"
) -> pd.DataFrame:
    """
    Calculate the high, low and range for each trading day.

    Expects a datetime column containing timezone-aware timestamps.
    """

    required_columns = {"datetime", "high", "low"}

    if not required_columns.issubset(df.columns):
        raise ValueError(
            "Candle data must contain datetime, high and low columns."
        )

    if df.empty:
        raise ValueError("Cannot calculate daily ranges from empty data.")

    data = df.copy()
    data["datetime"] = pd.to_datetime(data["datetime"], utc=True)

    data["trading_date"] = (
        data["datetime"]
        .dt.tz_convert(timezone)
        .dt.date
    )

    daily = (
        data.groupby("trading_date")
        .agg(
            high=("high", "max"),
            low=("low", "min"),
            candle_count=("high", "size")
        )
        .reset_index()
    )

    daily["range_points"] = (daily["high"] - daily["low"]).round(2)

    daily["range_percent"] = (
        daily["range_points"] / daily["low"] * 100
    ).round(4)

    return daily

def calculate_session_ranges(
    df: pd.DataFrame,
    session_name: str,
) -> pd.DataFrame:
    """
    Calculate historical ranges for a configured trading session.

    Uses Candle Fetcher's existing session definitions.
    """

    config = get_session_config(session_name)

    if session_name.strip().lower() == "all_sessions":
        return calculate_daily_ranges(
            df,
            timezone=config["timezone"],
        )

    filtered = filter_by_session(df, session_name)

    if filtered.empty:
        return pd.DataFrame(
            columns=[
                "trading_date", "session", "high", "low",
                "candle_count", "range_points", "range_percent"
            ]
        )

    results = calculate_daily_ranges(
        filtered,
        timezone=config["timezone"],
    )

    results.insert(
        1,
        "session",
        session_name.strip().lower(),
    )

    return results

def calculate_session_ranges_with_quality(
    df: pd.DataFrame,
    session_name: str,
    reference_start: str | None = None,
) -> pd.DataFrame:
    """
    Calculate historical session ranges with candle
    coverage and data-quality information.
    """

    range_data = df

    if reference_start is not None:
        config = get_session_config(session_name)

        local_times = pd.to_datetime(
            df["datetime"], utc=True
        ).dt.tz_convert(config["timezone"])

        reference_time = pd.Timestamp(
            f"2000-01-01 {reference_start}"
        ).time()

        range_data = df.loc[
            local_times.dt.time >= reference_time
        ].copy()

    ranges = calculate_session_ranges(
        range_data,
        session_name,
    )

    if ranges.empty:
        return ranges.assign(
            expected_candles=pd.Series(dtype="int64"),
            missing_candles=pd.Series(dtype="int64"),
            duplicate_candles=pd.Series(dtype="int64"),
            first_candle_matches=pd.Series(dtype="bool"),
            last_candle_matches=pd.Series(dtype="bool"),
            is_complete=pd.Series(dtype="bool"),
        )
    
    config = get_session_config(session_name)

    quality_data = filter_by_session(
        df, session_name
    ).copy()

    quality_data["quality_date"] = (
        pd.to_datetime(
            quality_data["datetime"], utc=True
        )
        .dt.tz_convert(config["timezone"])
        .dt.date
    )

    quality_by_date = {
        date: group.drop(columns="quality_date")
        for date, group in quality_data.groupby("quality_date")
    }

    quality_reports = []

    for trading_date in ranges["trading_date"]:
        report = validate_session_coverage(
            quality_by_date[
                pd.Timestamp(trading_date).date()
            ],
            session_name=session_name,
            trading_date=str(trading_date),
            reference_start=reference_start,
        )

        quality_reports.append(report)

    quality_df = pd.DataFrame(quality_reports)
    
    quality_df["trading_date"] = pd.to_datetime(
        quality_df["trading_date"]
    ).dt.date

    return ranges.merge(
        quality_df[
            [
                "trading_date",
                "expected_candles",
                "missing_candles",
                "duplicate_candles",
                "first_candle_matches",
                "last_candle_matches",
                "is_complete",
            ]
        ],
        on="trading_date",
        how="left",
        validate="one_to_one",
    )