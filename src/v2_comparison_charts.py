from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go


# --------------------------------------------------
# Candle Fetcher 2.0 — Chart theme
# --------------------------------------------------

BACKGROUND = "#0F1724"
TEXT_COLOR = "#E5EDF7"
MUTED_COLOR = "#94A3B8"
GRID_COLOR = "#273449"

CHART_COLORS = [
    "#3B82F6",
    "#22D3EE",
    "#818CF8",
    "#38BDF8",
    "#A78BFA",
]


# --------------------------------------------------
# Volatility Score Comparison
# --------------------------------------------------

def build_volatility_score_chart(result: dict) -> go.Figure:
    """
    Build a polished, interactive volatility score chart.

    Uses the original CSV Comparison engine's calculated
    values without modifying or recalculating them.
    """

    summary = result["raw_result"]["regime_summary"]

    required_columns = {
        "label",
        "volatility_score",
        "regime",
        "rows",
    }

    missing = required_columns - set(summary.columns)

    if missing:
        raise ValueError(
            f"Missing chart columns: {sorted(missing)}"
        )

    if summary.empty:
        raise ValueError(
            "Cannot generate a chart from empty results."
        )

    labels = summary["label"].astype(str).tolist()

    scores = pd.to_numeric(
        summary["volatility_score"],
        errors="raise",
    ).tolist()

    if not all(
        math.isfinite(score) and 0 <= score <= 100
        for score in scores
    ):
        raise ValueError(
            "Volatility scores must be finite values from 0 to 100."
        )

    regimes = summary["regime"].astype(str).tolist()
    candle_counts = summary["rows"].astype(int).tolist()

    hover_data = list(zip(regimes, candle_counts))

    colors = [
        CHART_COLORS[index % len(CHART_COLORS)]
        for index in range(len(labels))
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=labels,
            y=scores,
            width=0.42,
            marker=dict(
                color=colors,
                line=dict(width=0),
                opacity=0.96,
            ),
            customdata=hover_data,
            text=[
                f"{score:.1f}"
                for score in scores
            ],
            textposition="outside",
            textfont=dict(
                color=TEXT_COLOR,
                size=15,
            ),
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b>"
                "<br>Volatility score: %{y:.2f}/100"
                "<br>Regime: %{customdata[0]}"
                "<br>Candles: %{customdata[1]}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text=(
                "Volatility Score Comparison"
                "<br><sup>"
                "Relative to selected datasets — "
                "not probabilities or universal thresholds"
                "</sup>"
            ),
            font=dict(
                size=23,
                color=TEXT_COLOR,
            ),
            x=0.04,
            xanchor="left",
        ),
        paper_bgcolor=BACKGROUND,
        plot_bgcolor=BACKGROUND,
        font=dict(
            family="Arial",
            color=TEXT_COLOR,
            size=13,
        ),
        xaxis=dict(
            title="Selected Dataset",
            showgrid=False,
            zeroline=False,
            tickfont=dict(
                color=TEXT_COLOR,
                size=13,
            ),
        ),
        yaxis=dict(
            title="Comparative Volatility Score (0–100)",
            range=[0, 110],
            tickvals=[0, 25, 50, 75, 100],
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickfont=dict(
                color=MUTED_COLOR,
                size=12,
            ),
        ),
        margin=dict(
            l=90,
            r=45,
            t=125,
            b=85,
        ),
        height=500,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_color=TEXT_COLOR,
        ),
        bargap=0.55,
    )

    return fig
