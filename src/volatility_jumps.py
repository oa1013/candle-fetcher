from __future__ import annotations

from pathlib import Path

import pandas as pd

from .loaders import load_candle_csv


# ---------------------------------------------------------------------------
# Preparation
# ---------------------------------------------------------------------------

def prepare_jump_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare candle data for volatility jump analysis.

    Expected columns:
        datetime, open, high, low, close
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
    output["abs_close_return"] = output["close_return"].abs()

    output["price_move"] = output["close"] - output["open"]
    output["price_move_pct"] = (output["price_move"] / output["open"]) * 100

    if "tick_volume" not in output.columns:
        output["tick_volume"] = 0

    if "spread" not in output.columns:
        output["spread"] = 0

    return output


# ---------------------------------------------------------------------------
# Jump scoring
# ---------------------------------------------------------------------------

def add_jump_scores(
    df: pd.DataFrame,
    rolling_window: int = 100,
) -> pd.DataFrame:
    """
    Add rolling volatility baseline and jump score.

    The jump score measures how unusual the current candle range is
    compared with the recent rolling range behavior.
    """

    if rolling_window < 5:
        raise ValueError("rolling_window must be at least 5.")

    output = prepare_jump_dataframe(df)

    min_periods = max(5, rolling_window // 5)

    output["rolling_range_mean"] = (
        output["candle_range"]
        .rolling(window=rolling_window, min_periods=min_periods)
        .mean()
        .shift(1)
    )

    output["rolling_range_std"] = (
        output["candle_range"]
        .rolling(window=rolling_window, min_periods=min_periods)
        .std()
        .shift(1)
    )

    output["rolling_atr"] = output["rolling_range_mean"]

    output["jump_score"] = (
        (output["candle_range"] - output["rolling_range_mean"])
        / output["rolling_range_std"].replace(0, pd.NA)
    )

    output["range_to_baseline"] = (
        output["candle_range"]
        / output["rolling_range_mean"].replace(0, pd.NA)
    )

    output["jump_score"] = pd.to_numeric(output["jump_score"], errors="coerce")
    output["range_to_baseline"] = pd.to_numeric(output["range_to_baseline"], errors="coerce")

    return output


def classify_jump_score(jump_score: float) -> str:
    """
    Classify a jump score into a simple label.
    """

    if pd.isna(jump_score):
        return "unknown"

    if jump_score >= 4:
        return "extreme"

    if jump_score >= 2:
        return "volatile"

    return "normal"


def detect_volatility_jumps(
    df: pd.DataFrame,
    rolling_window: int = 100,
    threshold: float = 2.0,
) -> pd.DataFrame:
    """
    Detect volatility jumps.

    A jump is detected when jump_score is greater than or equal to threshold.
    """

    output = add_jump_scores(
        df=df,
        rolling_window=rolling_window,
    )

    output["is_jump"] = output["jump_score"] >= threshold
    output["jump_regime"] = output["jump_score"].apply(classify_jump_score)

    return output


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

def get_top_volatility_jumps(
    df: pd.DataFrame,
    rolling_window: int = 100,
    threshold: float = 2.0,
    top_n: int = 20,
) -> pd.DataFrame:
    """
    Return the biggest volatility jumps.
    """

    jump_df = detect_volatility_jumps(
        df=df,
        rolling_window=rolling_window,
        threshold=threshold,
    )

    jumps = jump_df[jump_df["is_jump"]].copy()

    if jumps.empty:
        return jumps

    jumps = jumps.sort_values(
        "jump_score",
        ascending=False,
    ).reset_index(drop=True)

    if top_n is not None:
        jumps = jumps.head(top_n)

    jumps.insert(0, "rank", range(1, len(jumps) + 1))

    return jumps


def find_volatility_jumps_from_csv(
    csv_path: str | Path,
    rolling_window: int = 100,
    threshold: float = 2.0,
    top_n: int = 20,
) -> pd.DataFrame:
    """
    Load a CSV and return the biggest volatility jumps.
    """

    df = load_candle_csv(csv_path)

    return get_top_volatility_jumps(
        df=df,
        rolling_window=rolling_window,
        threshold=threshold,
        top_n=top_n,
    )


def summarize_volatility_jumps(
    df: pd.DataFrame,
    rolling_window: int = 100,
    threshold: float = 2.0,
) -> dict:
    """
    Return a simple summary of volatility jumps.
    """

    jump_df = detect_volatility_jumps(
        df=df,
        rolling_window=rolling_window,
        threshold=threshold,
    )

    jumps = jump_df[jump_df["is_jump"]].copy()

    if jumps.empty:
        return {
            "total_rows": len(jump_df),
            "total_jumps": 0,
            "largest_jump_score": None,
            "average_jump_score": None,
            "first_jump_datetime": None,
            "last_jump_datetime": None,
        }

    return {
        "total_rows": len(jump_df),
        "total_jumps": len(jumps),
        "largest_jump_score": jumps["jump_score"].max(),
        "average_jump_score": jumps["jump_score"].mean(),
        "first_jump_datetime": jumps["datetime"].min(),
        "last_jump_datetime": jumps["datetime"].max(),
    }


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_volatility_jump_table(jump_df: pd.DataFrame) -> pd.DataFrame:
    """
    Make the volatility jump table easier to read.
    """

    if jump_df.empty:
        return jump_df.copy()

    columns = [
        "rank",
        "datetime",
        "jump_score",
        "jump_regime",
        "price_move_pct",
        "candle_range",
        "rolling_atr",
        "range_to_baseline",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
    ]

    available_columns = [
        column for column in columns
        if column in jump_df.columns
    ]

    output = jump_df[available_columns].copy()

    round_columns = {
        "jump_score": 2,
        "price_move_pct": 3,
        "candle_range": 2,
        "rolling_atr": 2,
        "range_to_baseline": 2,
        "open": 2,
        "high": 2,
        "low": 2,
        "close": 2,
        "tick_volume": 0,
        "spread": 2,
    }

    for column, decimals in round_columns.items():
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce").round(decimals)

    output = output.rename(
        columns={
            "rank": "Rank",
            "datetime": "Datetime",
            "jump_score": "Jump Score",
            "jump_regime": "Jump Regime",
            "price_move_pct": "Price Move %",
            "candle_range": "Candle Range",
            "rolling_atr": "Rolling ATR",
            "range_to_baseline": "Range vs Baseline",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "tick_volume": "Tick Volume",
            "spread": "Spread",
        }
    )

    return output


def print_volatility_jump_results(jump_df: pd.DataFrame) -> None:
    """
    Print a clean volatility jump table.
    """

    if jump_df.empty:
        print("No volatility jumps found.")
        return

    friendly_table = format_volatility_jump_table(jump_df)

    print("Top Volatility Jumps")
    print("Higher jump score = larger volatility jump compared with recent candles.")
    print()
    print(friendly_table.to_string(index=False))