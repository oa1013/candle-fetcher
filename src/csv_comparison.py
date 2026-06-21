from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Iterable

import pandas as pd

from .loaders import load_candle_csv
from .regime_analysis import (
    add_regime_labels,
    calculate_regime_metrics,
    prepare_regime_dataframe,
    summarize_regimes,
)


# ---------------------------------------------------------------------------
# Metric similarity
# ---------------------------------------------------------------------------

SIMILARITY_METRICS = [
    "median_range",
    "range_std",
    "max_range",
    "return_std",
    "avg_abs_return",
    "avg_tick_volume",
    "avg_spread",
]


def calculate_metric_similarity(
    metrics_a: dict,
    metrics_b: dict,
    metric_names: Iterable[str] = SIMILARITY_METRICS,
) -> dict:
    """
    Compare two metric dictionaries and return a similarity percentage.

    Each metric gets a 0-100 similarity score.
    The final metric_similarity_pct is the average.
    """
    metric_scores = {}

    for metric_name in metric_names:
        value_a = metrics_a.get(metric_name)
        value_b = metrics_b.get(metric_name)

        if value_a is None or value_b is None:
            continue

        if pd.isna(value_a) or pd.isna(value_b):
            continue

        value_a = float(value_a)
        value_b = float(value_b)

        denominator = max(abs(value_a), abs(value_b), 1e-12)
        difference_pct = abs(value_a - value_b) / denominator

        similarity = max(0.0, 1.0 - difference_pct) * 100
        metric_scores[f"{metric_name}_similarity"] = similarity

    if not metric_scores:
        overall_similarity = None
    else:
        overall_similarity = sum(metric_scores.values()) / len(metric_scores)

    return {
        "metric_similarity_pct": overall_similarity,
        **metric_scores,
    }


# ---------------------------------------------------------------------------
# Aligned return similarity
# ---------------------------------------------------------------------------

def calculate_aligned_return_similarity(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    min_overlap_rows: int = 30,
) -> dict:
    """
    Compare returns when two CSVs share matching timestamps.

    This is useful when files overlap in time.
    If there is not enough timestamp overlap, the result is None.
    """
    prepared_a = prepare_regime_dataframe(df_a)
    prepared_b = prepare_regime_dataframe(df_b)

    a = prepared_a[["datetime", "close_return"]].rename(
        columns={"close_return": "close_return_a"}
    )

    b = prepared_b[["datetime", "close_return"]].rename(
        columns={"close_return": "close_return_b"}
    )

    merged = pd.merge(a, b, on="datetime", how="inner")
    merged = merged.dropna(subset=["close_return_a", "close_return_b"])

    overlap_rows = len(merged)

    if overlap_rows < min_overlap_rows:
        return {
            "overlap_rows": overlap_rows,
            "return_correlation": None,
            "aligned_similarity_pct": None,
        }

    correlation = merged["close_return_a"].corr(merged["close_return_b"])

    if pd.isna(correlation):
        aligned_similarity = None
    else:
        # Convert correlation from -1..1 into 0..100.
        aligned_similarity = ((correlation + 1) / 2) * 100

    return {
        "overlap_rows": overlap_rows,
        "return_correlation": correlation,
        "aligned_similarity_pct": aligned_similarity,
    }


# ---------------------------------------------------------------------------
# Pair comparison
# ---------------------------------------------------------------------------

def compare_metric_rows(
    row_a: pd.Series,
    row_b: pd.Series,
    df_a: pd.DataFrame | None = None,
    df_b: pd.DataFrame | None = None,
) -> dict:
    """
    Compare two metric rows and return a pairwise comparison result.
    """
    metrics_a = row_a.to_dict()
    metrics_b = row_b.to_dict()

    metric_similarity = calculate_metric_similarity(
        metrics_a=metrics_a,
        metrics_b=metrics_b,
    )

    aligned_similarity = {
        "overlap_rows": None,
        "return_correlation": None,
        "aligned_similarity_pct": None,
    }

    if df_a is not None and df_b is not None:
        aligned_similarity = calculate_aligned_return_similarity(
            df_a=df_a,
            df_b=df_b,
        )

    if aligned_similarity["aligned_similarity_pct"] is not None:
        overall_similarity = (
            metric_similarity["metric_similarity_pct"] * 0.70
            + aligned_similarity["aligned_similarity_pct"] * 0.30
        )
    else:
        overall_similarity = metric_similarity["metric_similarity_pct"]

    return {
        "label_a": metrics_a.get("label"),
        "label_b": metrics_b.get("label"),
        "regime_a": metrics_a.get("regime"),
        "regime_b": metrics_b.get("regime"),
        "volatility_score_a": metrics_a.get("volatility_score"),
        "volatility_score_b": metrics_b.get("volatility_score"),
        "metric_similarity_pct": metric_similarity["metric_similarity_pct"],
        "aligned_similarity_pct": aligned_similarity["aligned_similarity_pct"],
        "return_correlation": aligned_similarity["return_correlation"],
        "overlap_rows": aligned_similarity["overlap_rows"],
        "overall_similarity_pct": overall_similarity,
        "conclusion": interpret_similarity(overall_similarity),
    }


def interpret_similarity(similarity_pct: float | None) -> str:
    """Convert a similarity percentage into a plain-English conclusion."""
    if similarity_pct is None:
        return "Not enough data to compare."

    if similarity_pct >= 85:
        return "Very similar"

    if similarity_pct >= 70:
        return "Moderately similar"

    if similarity_pct >= 50:
        return "Somewhat different"

    return "Very different"


def build_pairwise_comparisons(
    metrics_df: pd.DataFrame,
    loaded_dataframes: dict[str, pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """
    Build a pairwise comparison table from a metrics DataFrame.
    """
    if metrics_df.empty or len(metrics_df) < 2:
        return pd.DataFrame()

    comparisons = []

    for index_a, index_b in combinations(metrics_df.index, 2):
        row_a = metrics_df.loc[index_a]
        row_b = metrics_df.loc[index_b]

        label_a = row_a["label"]
        label_b = row_b["label"]

        df_a = None
        df_b = None

        if loaded_dataframes is not None:
            df_a = loaded_dataframes.get(label_a)
            df_b = loaded_dataframes.get(label_b)

        comparisons.append(
            compare_metric_rows(
                row_a=row_a,
                row_b=row_b,
                df_a=df_a,
                df_b=df_b,
            )
        )

    comparison_df = pd.DataFrame(comparisons)

    if "overall_similarity_pct" in comparison_df.columns:
        comparison_df = comparison_df.sort_values(
            "overall_similarity_pct",
            ascending=False,
        ).reset_index(drop=True)

    return comparison_df


# ---------------------------------------------------------------------------
# CSV comparison workflows
# ---------------------------------------------------------------------------

def compare_csv_files(
    csv_paths: Iterable[str | Path],
    labels: Iterable[str] | None = None,
) -> dict:
    """
    Compare multiple CSV files.

    Returns:
        {
            "regime_summary": DataFrame,
            "pairwise_comparisons": DataFrame,
            "metrics": DataFrame,
        }
    """
    csv_paths = [Path(path) for path in csv_paths]

    if labels is None:
        labels = [path.stem for path in csv_paths]
    else:
        labels = list(labels)

    if len(csv_paths) != len(labels):
        raise ValueError("csv_paths and labels must have the same length.")

    metrics = []
    loaded_dataframes = {}

    for csv_path, label in zip(csv_paths, labels):
        df = load_candle_csv(csv_path)

        loaded_dataframes[label] = df

        metrics.append(
            calculate_regime_metrics(
                df=df,
                label=label,
                source_path=str(csv_path),
            )
        )

    metrics_df = pd.DataFrame(metrics)
    metrics_df = add_regime_labels(metrics_df)

    regime_summary = summarize_regimes(metrics_df)

    pairwise_comparisons = build_pairwise_comparisons(
        metrics_df=metrics_df,
        loaded_dataframes=loaded_dataframes,
    )

    return {
        "regime_summary": regime_summary,
        "pairwise_comparisons": pairwise_comparisons,
        "metrics": metrics_df,
    }


def compare_two_csvs(
    csv_a: str | Path,
    csv_b: str | Path,
    label_a: str = "csv_a",
    label_b: str = "csv_b",
) -> dict:
    """
    Compare two CSV files.
    """
    return compare_csv_files(
        csv_paths=[csv_a, csv_b],
        labels=[label_a, label_b],
    )


def print_comparison_summary(result: dict) -> None:
    """Print a clean text summary of comparison results."""
    regime_summary = result["regime_summary"]
    pairwise = result["pairwise_comparisons"]

    print("Regime Summary")
    print(regime_summary)

    print("\nPairwise Comparisons")
    print(pairwise)