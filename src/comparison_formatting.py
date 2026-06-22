from __future__ import annotations

import pandas as pd


def round_existing_columns(
    df: pd.DataFrame,
    decimals_by_column: dict[str, int],
) -> pd.DataFrame:
    """
    Round selected numeric columns if they exist.
    """
    output = df.copy()

    for column, decimals in decimals_by_column.items():
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce").round(decimals)

    return output


def format_regime_summary_table(regime_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Make the regime summary table easier to read.
    """
    if regime_summary.empty:
        return regime_summary.copy()

    columns = [
        "label",
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
        if column in regime_summary.columns
    ]

    output = regime_summary[available_columns].copy()

    output = round_existing_columns(
        df=output,
        decimals_by_column={
            "volatility_score": 1,
            "avg_range": 2,
            "median_range": 2,
            "max_range": 2,
            "return_std": 6,
            "avg_tick_volume": 0,
            "avg_spread": 2,
        },
    )

    output = output.rename(
        columns={
            "label": "CSV Name",
            "rows": "Rows",
            "first_datetime": "First Candle",
            "last_datetime": "Last Candle",
            "regime": "Regime",
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


def format_pairwise_comparison_table(pairwise_comparisons: pd.DataFrame) -> pd.DataFrame:
    """
    Make the pairwise comparison table easier to read.
    """
    if pairwise_comparisons.empty:
        return pairwise_comparisons.copy()

    columns = [
        "label_a",
        "label_b",
        "regime_a",
        "regime_b",
        "overall_similarity_pct",
        "metric_similarity_pct",
        "aligned_similarity_pct",
        "return_correlation",
        "overlap_rows",
        "conclusion",
    ]

    available_columns = [
        column for column in columns
        if column in pairwise_comparisons.columns
    ]

    output = pairwise_comparisons[available_columns].copy()

    output = round_existing_columns(
        df=output,
        decimals_by_column={
            "overall_similarity_pct": 1,
            "metric_similarity_pct": 1,
            "aligned_similarity_pct": 1,
            "return_correlation": 3,
            "overlap_rows": 0,
        },
    )

    output = output.rename(
        columns={
            "label_a": "CSV A",
            "label_b": "CSV B",
            "regime_a": "Regime A",
            "regime_b": "Regime B",
            "overall_similarity_pct": "Overall Similarity %",
            "metric_similarity_pct": "Metric Similarity %",
            "aligned_similarity_pct": "Time-Aligned Similarity %",
            "return_correlation": "Return Correlation",
            "overlap_rows": "Overlapping Candles",
            "conclusion": "Conclusion",
        }
    )

    return output


def build_user_friendly_comparison_tables(result: dict) -> dict:
    """
    Build user-friendly versions of the comparison output tables.
    """
    return {
        "regime_summary": format_regime_summary_table(result["regime_summary"]),
        "pairwise_comparisons": format_pairwise_comparison_table(result["pairwise_comparisons"]),
        "metrics": result["metrics"],
    }


def print_user_friendly_comparison_summary(result: dict) -> None:
    """
    Print comparison results in a cleaner, easier-to-understand way.
    """
    friendly_tables = build_user_friendly_comparison_tables(result)

    regime_summary = friendly_tables["regime_summary"]
    pairwise_comparisons = friendly_tables["pairwise_comparisons"]

    print("Regime Summary")
    print("This table shows which CSVs look calm, normal, volatile, or extreme.")
    print()

    if regime_summary.empty:
        print("No regime summary rows available.")
    else:
        print(regime_summary.to_string(index=False))

    print()
    print("Pairwise Similarity")
    print("This table compares each CSV against the others.")
    print()

    if pairwise_comparisons.empty:
        print("No pairwise comparison rows available.")
    else:
        print(pairwise_comparisons.to_string(index=False))