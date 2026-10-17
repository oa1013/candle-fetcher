
import pandas as pd


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
