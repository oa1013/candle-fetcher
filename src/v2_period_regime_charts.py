from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go


# --------------------------------------------------
# Candle Fetcher 2.0 — Period Regime Charts
# --------------------------------------------------

BACKGROUND = "#0F1724"
TEXT_COLOR = "#E5EDF7"
MUTED_COLOR = "#94A3B8"
GRID_COLOR = "#273449"

# Cool = lower relative volatility.
# Hot = higher relative volatility.
VOLATILITY_COLORS = [
    [0.00, "#2563EB"],
    [0.25, "#22D3EE"],
    [0.50, "#FACC15"],
    [0.75, "#F97316"],
    [1.00, "#DC2626"],
]


def build_period_regime_ranking_chart(
    result: dict,
) -> go.Figure:
    """
    Build an interactive ranking chart for the
    calmest or most volatile market periods.

    Uses the original Period Regime Finder's
    calculated metrics without recalculating them.

    Supports year, month, week and day rankings.
    """

    if result.get("status") != "completed":
        raise ValueError(
            "A completed Period Regime result is required."
        )

    data = result["raw_results"]

    required_columns = {
        "rank",
        "period_label",
        "volatility_score",
        "regime",
        "rows",
        "avg_range",
    }

    missing = required_columns - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing chart columns: {sorted(missing)}"
        )

    if data.empty:
        raise ValueError(
            "Cannot create a ranking chart from empty data."
        )

    # ------------------------------------------
    # Read the original engine results
    # ------------------------------------------

    labels = data["period_label"].astype(str).tolist()

    scores = pd.to_numeric(
        data["volatility_score"],
        errors="raise",
    ).astype(float).tolist()

    ranks = pd.to_numeric(
        data["rank"],
        errors="raise",
    ).astype(int).tolist()

    regimes = data["regime"].astype(str).tolist()

    candle_counts = pd.to_numeric(
        data["rows"],
        errors="raise",
    ).astype(int).tolist()

    average_ranges = pd.to_numeric(
        data["avg_range"],
        errors="raise",
    ).astype(float).tolist()

    if len(set(labels)) != len(labels):
        raise ValueError(
            "Period labels must be unique."
        )

    if not all(
        math.isfinite(score) and 0 <= score <= 100
        for score in scores
    ):
        raise ValueError(
            "Volatility scores must be finite and within 0–100."
        )

    if not all(
        math.isfinite(value)
        for value in average_ranges
    ):
        raise ValueError(
            "Average candle ranges must be finite."
        )

    if any(count < 1 for count in candle_counts):
        raise ValueError(
            "Each period must contain at least one candle."
        )

    # ------------------------------------------
    # Dynamic chart title
    # ------------------------------------------

    period_type = result["period"].capitalize()

    if result["regime"] == "calm":
        ranking_title = f"Calmest {period_type}s"
    else:
        ranking_title = f"Most Volatile {period_type}s"

    title = (
        f"{ranking_title}"
        "<br><sup>"
        "Relative volatility ranking — "
        "scores are not probabilities"
        "</sup>"
    )

    # ------------------------------------------
    # Plotly figure
    # ------------------------------------------

    fig = go.Figure()

    hover_data = list(
        zip(
            ranks,
            regimes,
            candle_counts,
            average_ranges,
        )
    )

    fig.add_trace(
        go.Bar(
            orientation="h",
            x=scores,
            y=labels,
            width=0.55,
            marker=dict(
                color=scores,
                colorscale=VOLATILITY_COLORS,
                cmin=0,
                cmax=100,
                line=dict(width=0),
                showscale=True,
                colorbar=dict(
                    title=dict(
                        text="Volatility",
                    ),
                    thickness=15,
                    len=0.8,
                    tickvals=[0, 25, 50, 75, 100],
                    outlinewidth=0,
                ),
            ),
            customdata=hover_data,
            text=[
                f"{score:.1f}"
                for score in scores
            ],
            textposition="outside",
            textfont=dict(
                color=TEXT_COLOR,
                size=14,
            ),
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b>"
                "<br>Rank: %{customdata[0]}"
                "<br>Volatility score: %{x:.2f}/100"
                "<br>Regime: %{customdata[1]}"
                "<br>Candles: %{customdata[2]:,}"
                "<br>Average candle range: %{customdata[3]:.2f}"
                "<extra></extra>"
            ),
        )
    )

    # ------------------------------------------
    # Premium dark theme
    # ------------------------------------------

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(
                color=TEXT_COLOR,
                size=23,
            ),
            x=0.04,
        ),

        paper_bgcolor=BACKGROUND,
        plot_bgcolor=BACKGROUND,

        font=dict(
            family="Arial",
            color=TEXT_COLOR,
            size=13,
        ),

        xaxis=dict(
            title="Relative Volatility Score (0–100)",
            range=[0, 112],
            tickvals=[0, 25, 50, 75, 100],
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickfont=dict(
                color=MUTED_COLOR,
            ),
        ),

        yaxis=dict(
            title="Period",
            type="category",
            autorange="reversed",
            showgrid=False,
            zeroline=False,
            tickfont=dict(
                color=TEXT_COLOR,
                size=13,
            ),
        ),

        margin=dict(
            l=125,
            r=110,
            t=130,
            b=90,
        ),

        height=max(
            480,
            200 + len(labels) * 58,
        ),

        showlegend=False,

        hoverlabel=dict(
            bgcolor="#1E293B",
            font_color=TEXT_COLOR,
        ),

        bargap=0.35,
    )

    return fig
