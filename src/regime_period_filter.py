from __future__ import annotations

from pathlib import Path

import pandas as pd

from .loaders import load_candle_csv
from .regime_analysis import add_regime_labels, calculate_regime_metrics


PERIOD_ALIASES = {
    "year": "year",
    "years": "year",
    "y": "year",

    "month": "month",
    "months": "month",
    "m": "month",

    "week": "week",
    "weeks": "week",
    "w": "week",

    "day": "day",
    "days": "day",
    "d": "day",
}


REGIME_ALIASES = {
    "calm": "calm",
    "calmest": "calm",
    "low": "calm",
    "lowest": "calm",

    "volatile": "volatile",
    "most_volatile": "volatile",
    "high": "volatile",
    "highest": "volatile",
}


def normalize_period(period: str) -> str:
    """
    Normalize user period input.

    Examples:
        years -> year
        months -> month
        weeks -> week
        days -> day
    """

    period = str(period).strip().lower()

    if period not in PERIOD_ALIASES:
        raise ValueError(
            f"Unsupported period: {period}. "
            "Use one of: year, month, week, day."
        )

    return PERIOD_ALIASES[period]


def normalize_regime(regime: str) -> str:
    """
    Normalize user regime input.

    Examples:
        calmest -> calm
        most_volatile -> volatile
    """

    regime = str(regime).strip().lower()

    if regime not in REGIME_ALIASES:
        raise ValueError(
            f"Unsupported regime: {regime}. "
            "Use one of: calm, volatile."
        )

    return REGIME_ALIASES[regime]


def add_period_label(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    Add a period_label column to candle data.

    period can be:
        year
        month
        week
        day
    """

    period = normalize_period(period)

    output = df.copy()
    output["datetime"] = pd.to_datetime(
        output["datetime"],
        utc=True,
        errors="coerce",
    )

    output = output.dropna(subset=["datetime"])
    output = output.sort_values("datetime").reset_index(drop=True)

    if period == "year":
        output["period_label"] = output["datetime"].dt.strftime("%Y")

    elif period == "month":
        output["period_label"] = output["datetime"].dt.strftime("%Y-%m")

    elif period == "week":
        output["period_label"] = output["datetime"].dt.strftime("%G-W%V")

    elif period == "day":
        output["period_label"] = output["datetime"].dt.strftime("%Y-%m-%d")

    else:
        raise ValueError(f"Unsupported period: {period}")

    return output


def calculate_period_regime_metrics(
    df: pd.DataFrame,
    period: str,
) -> pd.DataFrame:
    """
    Split candle data into periods and calculate volatility metrics for each period.
    """

    period = normalize_period(period)
    labelled_df = add_period_label(df=df, period=period)

    if labelled_df.empty:
        raise ValueError("No candles available after preparing period labels.")

    metrics = []

    for period_label, period_df in labelled_df.groupby("period_label"):
        period_metrics = calculate_regime_metrics(
            df=period_df,
            label=str(period_label),
        )

        period_metrics["period"] = period
        period_metrics["period_label"] = str(period_label)

        metrics.append(period_metrics)

    metrics_df = pd.DataFrame(metrics)

    if metrics_df.empty:
        raise ValueError("No period metrics were calculated.")

    metrics_df = add_regime_labels(metrics_df)

    return metrics_df


def find_period_regimes(
    df: pd.DataFrame,
    period: str,
    regime: str,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Find the calmest or most volatile periods inside candle data.

    Examples:
        find_period_regimes(df, period="year", regime="calm")
        find_period_regimes(df, period="month", regime="volatile")
    """

    period = normalize_period(period)
    regime = normalize_regime(regime)

    metrics_df = calculate_period_regime_metrics(
        df=df,
        period=period,
    )

    ascending = regime == "calm"

    ranked = metrics_df.sort_values(
        "volatility_score",
        ascending=ascending,
    ).reset_index(drop=True)

    ranked.insert(0, "rank", range(1, len(ranked) + 1))

    if top_n is not None:
        ranked = ranked.head(top_n)

    return ranked


def find_period_regimes_from_csv(
    csv_path: str | Path,
    period: str,
    regime: str,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Load one CSV and find the calmest or most volatile periods inside it.
    """

    df = load_candle_csv(csv_path)

    return find_period_regimes(
        df=df,
        period=period,
        regime=regime,
        top_n=top_n,
    )


def format_period_regime_table(result_df: pd.DataFrame) -> pd.DataFrame:
    """
    Make the period regime result table easier to read.
    """

    if result_df.empty:
        return result_df.copy()

    columns = [
        "rank",
        "period",
        "period_label",
        "rows",
        "first_datetime",
        "last_datetime",
        "regime",
        "volatility_score",
        "avg_range",
        "median_range",
        "max_range",
        "return_std",
        "avg_tick_volume",
        "avg_spread",
    ]

    available_columns = [
        column for column in columns
        if column in result_df.columns
    ]

    output = result_df[available_columns].copy()

    round_columns = {
        "volatility_score": 1,
        "avg_range": 2,
        "median_range": 2,
        "max_range": 2,
        "return_std": 6,
        "avg_tick_volume": 0,
        "avg_spread": 2,
    }

    for column, decimals in round_columns.items():
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce").round(decimals)

    output = output.rename(
        columns={
            "rank": "Rank",
            "period": "Period Type",
            "period_label": "Period",
            "rows": "Rows",
            "first_datetime": "First Candle",
            "last_datetime": "Last Candle",
            "regime": "Regime Label",
            "volatility_score": "Volatility Score",
            "avg_range": "Average Candle Range",
            "median_range": "Median Candle Range",
            "max_range": "Largest Candle Range",
            "return_std": "Return Volatility",
            "avg_tick_volume": "Average Tick Volume",
            "avg_spread": "Average Spread",
        }
    )

    return output


def print_period_regime_results(result_df: pd.DataFrame) -> None:
    """
    Print calm/volatile period results in a readable format.
    """

    if result_df.empty:
        print("No period regime results available.")
        return

    friendly_table = format_period_regime_table(result_df)

    print("Period Regime Results")
    print("Lower volatility score = calmer period.")
    print("Higher volatility score = more volatile period.")
    print()
    print(friendly_table.to_string(index=False))