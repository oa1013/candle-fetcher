from __future__ import annotations

from typing import Iterable

import pandas as pd


# ---------------------------------------------------------------------------
# Candle feature helpers
# ---------------------------------------------------------------------------

def prepare_regime_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare candle data for regime analysis.

    Expected columns:
        datetime, open, high, low, close

    Optional columns:
        tick_volume, spread
    """
    required_columns = ["datetime", "open", "high", "low", "close"]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    output = df.copy()

    output["datetime"] = pd.to_datetime(
        output["datetime"],
        utc=True,
        errors="coerce",
    )

    output = output.dropna(subset=["datetime"])
    output = output.sort_values("datetime").reset_index(drop=True)

    output["candle_range"] = output["high"] - output["low"]
    output["candle_body"] = (output["close"] - output["open"]).abs()

    output["close_change"] = output["close"].diff()
    output["close_return"] = output["close"].pct_change()

    output["absolute_close_change"] = output["close_change"].abs()
    output["absolute_close_return"] = output["close_return"].abs()

    if "tick_volume" not in output.columns:
        output["tick_volume"] = 0

    if "spread" not in output.columns:
        output["spread"] = 0

    return output


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def calculate_regime_metrics(
    df: pd.DataFrame,
    label: str | None = None,
    source_path: str | None = None,
) -> dict:
    """
    Calculate summary metrics for one candle DataFrame.

    These metrics are later used to classify calm/volatile regimes.
    """
    prepared = prepare_regime_dataframe(df)

    if prepared.empty:
        raise ValueError("Cannot calculate regime metrics for an empty DataFrame.")

    safe_range = prepared["candle_range"].replace(0, pd.NA)
    body_to_range = prepared["candle_body"] / safe_range

    metrics = {
        "label": label or "dataset",
        "source_path": source_path,
        "rows": len(prepared),
        "first_datetime": prepared["datetime"].iloc[0],
        "last_datetime": prepared["datetime"].iloc[-1],

        # Range behavior
        "avg_range": prepared["candle_range"].mean(),
        "median_range": prepared["candle_range"].median(),
        "range_std": prepared["candle_range"].std(),
        "max_range": prepared["candle_range"].max(),

        # Body behavior
        "avg_body": prepared["candle_body"].mean(),
        "median_body": prepared["candle_body"].median(),
        "body_to_range_ratio": body_to_range.mean(),

        # Close movement behavior
        "avg_abs_close_change": prepared["absolute_close_change"].mean(),
        "median_abs_close_change": prepared["absolute_close_change"].median(),
        "return_std": prepared["close_return"].std(),
        "avg_abs_return": prepared["absolute_close_return"].mean(),

        # Volume / spread behavior
        "avg_tick_volume": prepared["tick_volume"].mean(),
        "median_tick_volume": prepared["tick_volume"].median(),
        "avg_spread": prepared["spread"].mean(),
        "median_spread": prepared["spread"].median(),
    }

    return metrics


def metrics_to_dataframe(metrics: Iterable[dict]) -> pd.DataFrame:
    """Convert a list of metric dictionaries into a DataFrame."""
    return pd.DataFrame(list(metrics))


# ---------------------------------------------------------------------------
# Regime classification
# ---------------------------------------------------------------------------

def add_volatility_score(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 0-100 relative volatility score.

    The score is based on percentile ranks inside the comparison group.
    Higher score = more volatile compared with the other files.
    """
    if metrics_df.empty:
        return metrics_df.copy()

    output = metrics_df.copy()

    score_columns = [
        "median_range",
        "range_std",
        "max_range",
        "return_std",
        "avg_abs_return",
    ]

    available_score_columns = [
        column for column in score_columns
        if column in output.columns
    ]

    if not available_score_columns:
        raise ValueError("No volatility metric columns found.")

    rank_columns = []

    for column in available_score_columns:
        rank_column = f"{column}_rank"
        output[rank_column] = output[column].rank(pct=True)
        rank_columns.append(rank_column)

    output["volatility_score"] = output[rank_columns].mean(axis=1) * 100

    return output


def classify_volatility_score(score: float) -> str:
    """
    Convert a volatility score into a regime label.
    """
    if score < 35:
        return "calm"

    if score < 70:
        return "normal"

    if score < 90:
        return "volatile"

    return "extreme"


def add_regime_labels(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add volatility_score and regime labels to a metrics DataFrame.
    """
    if metrics_df.empty:
        return metrics_df.copy()

    output = add_volatility_score(metrics_df)

    if len(output) == 1:
        output["regime"] = "single_file_baseline"
        output["regime_description"] = (
            "Only one file was analyzed, so no relative regime comparison was possible."
        )
        return output

    output["regime"] = output["volatility_score"].apply(classify_volatility_score)

    output["regime_description"] = output["regime"].map(
        {
            "calm": "Lower volatility compared with the other files.",
            "normal": "Middle-range volatility compared with the other files.",
            "volatile": "Higher volatility compared with the other files.",
            "extreme": "Highest volatility group compared with the other files.",
        }
    )

    return output


# ---------------------------------------------------------------------------
# Summary helper
# ---------------------------------------------------------------------------

def summarize_regimes(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a clean regime summary table.
    """
    if metrics_df.empty:
        return metrics_df.copy()

    columns = [
        "label",
        "rows",
        "first_datetime",
        "last_datetime",
        "regime",
        "volatility_score",
        "avg_range",
        "median_range",
        "range_std",
        "max_range",
        "return_std",
        "avg_abs_return",
        "avg_tick_volume",
        "avg_spread",
    ]

    available_columns = [
        column for column in columns
        if column in metrics_df.columns
    ]

    return metrics_df[available_columns].copy()