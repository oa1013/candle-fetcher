from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go


# --------------------------------------------------
# Candle Fetcher 2.0 — Volatility Jump Charts
# --------------------------------------------------

BACKGROUND = "#0F1724"
TEXT_COLOR = "#E5EDF7"
MUTED_COLOR = "#94A3B8"
GRID_COLOR = "#273449"

JUMP_COLORS = [
    [0.00, "#2563EB"],
    [0.30, "#22D3EE"],
    [0.55, "#FACC15"],
    [0.75, "#F97316"],
    [1.00, "#DC2626"],
]


def build_top_volatility_jumps_chart(
    result: dict,
) -> go.Figure:
    """
    Build an interactive ranking of detected volatility jumps.

    Jump scores and classifications come directly from
    the original Volatility Jump detection engine.

    Colours indicate relative jump-score magnitude within
    the displayed ranking, not regime classifications.
    """

    if result.get("status") != "completed":
        raise ValueError(
            "A completed Volatility Jump result is required."
        )

    data = result["top_jumps"]

    required_columns = {
        "rank",
        "datetime",
        "jump_score",
        "jump_regime",
        "candle_range",
        "range_to_baseline",
        "price_move_pct",
    }

    missing = required_columns - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing chart columns: {sorted(missing)}"
        )

    if data.empty:
        raise ValueError(
            "No volatility jumps are available to plot."
        )

    # ------------------------------------------
    # Read original statistical results
    # ------------------------------------------

    timestamps = pd.to_datetime(
        data["datetime"],
        utc=True,
        errors="raise",
    )

    labels = [
        timestamp.strftime("%Y-%m-%d %H:%M UTC")
        for timestamp in timestamps
    ]

    scores = pd.to_numeric(
        data["jump_score"],
        errors="raise",
    ).astype(float).tolist()

    ranks = pd.to_numeric(
        data["rank"],
        errors="raise",
    ).astype(int).tolist()

    regimes = data[
        "jump_regime"
    ].astype(str).tolist()

    candle_ranges = pd.to_numeric(
        data["candle_range"],
        errors="raise",
    ).astype(float).tolist()

    range_ratios = pd.to_numeric(
        data["range_to_baseline"],
        errors="raise",
    ).astype(float).tolist()

    price_moves = pd.to_numeric(
        data["price_move_pct"],
        errors="raise",
    ).astype(float).tolist()

    # ------------------------------------------
    # Validate chart data
    # ------------------------------------------

    if len(set(labels)) != len(labels):
        raise ValueError(
            "Duplicate jump timestamps detected."
        )

    if not all(
        math.isfinite(score)
        for score in scores
    ):
        raise ValueError(
            "Jump scores must be finite."
        )

    if any(
        scores[i] < scores[i + 1]
        for i in range(len(scores) - 1)
    ):
        raise ValueError(
            "Top jumps must be ranked in descending order."
        )

    if not all(
        math.isfinite(value)
        for value in candle_ranges
    ):
        raise ValueError(
            "Candle ranges must be finite."
        )

    # ------------------------------------------
    # Interactive hover information
    # ------------------------------------------

    hover_data = list(
        zip(
            ranks,
            regimes,
            candle_ranges,
            range_ratios,
            price_moves,
        )
    )

    # Colour mapping is relative to selected top jumps.
    color_min = min(scores)
    color_max = max(scores)

    if color_min == color_max:
        color_max = color_min + 1.0

    # ------------------------------------------
    # Build horizontal ranking chart
    # ------------------------------------------

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            orientation="h",
            x=scores,
            y=labels,
            width=0.60,
            marker=dict(
                color=scores,
                colorscale=JUMP_COLORS,
                cmin=color_min,
                cmax=color_max,
                line=dict(width=0),
                showscale=True,
                colorbar=dict(
                    title=dict(text="Jump Score"),
                    thickness=16,
                    len=0.80,
                    outlinewidth=0,
                    tickfont=dict(color=TEXT_COLOR),
                ),
            ),
            customdata=hover_data,
            text=[
                f"{score:.2f}"
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
                "<br>Jump score: %{x:.2f}"
                "<br>Regime: %{customdata[1]}"
                "<br>Candle range: %{customdata[2]:.2f} points"
                "<br>Range / baseline: %{customdata[3]:.2f}x"
                "<br>Candle price move: %{customdata[4]:.3f}%"
                "<extra></extra>"
            ),
        )
    )

    # ------------------------------------------
    # Premium dark styling
    # ------------------------------------------

    fig.update_layout(
        title=dict(
            text=(
                "Top Volatility Jumps"
                "<br><sup>"
                "Ranked by jump score — "
                "not probabilities or percentages"
                "</sup>"
            ),
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
            title="Jump Score (rolling standard deviations)",
            range=[
                min(0.0, min(scores)),
                max(scores) * 1.15,
            ],
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickfont=dict(color=MUTED_COLOR),
        ),

        yaxis=dict(
            title="Jump Timestamp (UTC)",
            type="category",
            autorange="reversed",
            showgrid=False,
            zeroline=False,
            tickfont=dict(
                color=TEXT_COLOR,
                size=12,
            ),
        ),

        margin=dict(
            l=190,
            r=120,
            t=120,
            b=90,
        ),

        height=max(
            550,
            230 + len(labels) * 52,
        ),

        showlegend=False,

        hoverlabel=dict(
            bgcolor="#1E293B",
            font_color=TEXT_COLOR,
        ),

        bargap=0.35,
    )

    return fig


def build_daily_jump_frequency_chart(
    result: dict,
) -> go.Figure:
    """
    Build a daily volatility jump frequency chart.

    Daily rate = detected jumps / available candles.

    The rolling rate uses the preceding 10 observed
    trading sessions, including the current session.

    Original detection calculations remain unchanged.
    """

    if result.get("status") != "completed":
        raise ValueError(
            "A completed Volatility Jump result is required."
        )

    daily = result["daily_counts"]

    required_columns = {
        "date",
        "total_candles",
        "jump_count",
        "jump_rate_pct",
    }

    missing = required_columns - set(daily.columns)

    if missing:
        raise ValueError(
            f"Missing daily columns: {sorted(missing)}"
        )

    if daily.empty:
        raise ValueError(
            "No daily jump statistics are available."
        )

    # ------------------------------------------
    # Validate daily statistical data
    # ------------------------------------------

    dates = pd.to_datetime(
        daily["date"],
        utc=True,
        errors="raise",
    )

    if dates.isna().any():
        raise ValueError("Invalid daily timestamps.")

    if dates.duplicated().any():
        raise ValueError("Duplicate trading days.")

    if not dates.is_monotonic_increasing:
        raise ValueError(
            "Daily dates must be chronological."
        )

    candles = pd.to_numeric(
        daily["total_candles"],
        errors="raise",
    ).astype(float)

    jumps = pd.to_numeric(
        daily["jump_count"],
        errors="raise",
    ).astype(float)

    rates = pd.to_numeric(
        daily["jump_rate_pct"],
        errors="raise",
    ).astype(float)

    if not all(
        math.isfinite(float(value))
        for series in (candles, jumps, rates)
        for value in series
    ):
        raise ValueError(
            "Daily statistics must be finite."
        )

    if (candles <= 0).any():
        raise ValueError(
            "Daily candle counts must be positive."
        )

    if (jumps < 0).any() or (jumps > candles).any():
        raise ValueError(
            "Invalid daily jump counts."
        )

    calculated_rates = jumps / candles * 100

    if not all(
        math.isclose(
            float(actual),
            float(expected),
            rel_tol=0,
            abs_tol=1e-9,
        )
        for actual, expected in zip(
            rates,
            calculated_rates,
        )
    ):
        raise ValueError(
            "Daily rates do not match jump counts."
        )

    if int(jumps.sum()) != int(result["total_jumps"]):
        raise ValueError(
            "Daily jump totals do not match analysis."
        )

    if int(candles.sum()) != int(result["total_candles"]):
        raise ValueError(
            "Daily candle totals do not match analysis."
        )

    # ------------------------------------------
    # Trailing 10-session jump frequency
    # ------------------------------------------

    rolling_jumps = (
        jumps.rolling(
            window=10,
            min_periods=1,
        ).sum()
    )

    rolling_candles = (
        candles.rolling(
            window=10,
            min_periods=1,
        ).sum()
    )

    rolling_rate = (
        rolling_jumps / rolling_candles * 100
    )

    # ------------------------------------------
    # Create interactive chart
    # ------------------------------------------

    fig = go.Figure()

    hover_data = list(
        zip(
            jumps.astype(int),
            candles.astype(int),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=rates,
            mode="lines",
            name="Daily jump rate",
            line=dict(
                color="#2563EB",
                width=2,
            ),
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.12)",
            customdata=hover_data,
            hovertemplate=(
                "<b>%{x|%Y-%m-%d} UTC</b>"
                "<br>Daily jump rate: %{y:.2f}%"
                "<br>Detected jumps: %{customdata[0]}"
                "<br>Candles analysed: %{customdata[1]}"
                "<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=rolling_rate,
            mode="lines",
            name="10-session rolling rate",
            line=dict(
                color="#22D3EE",
                width=3,
            ),
            hovertemplate=(
                "<b>%{x|%Y-%m-%d} UTC</b>"
                "<br>10-session rolling rate: %{y:.2f}%"
                "<extra></extra>"
            ),
        )
    )

    # ------------------------------------------
    # Candle Fetcher 2.0 styling
    # ------------------------------------------

    fig.update_layout(
        title=dict(
            text=(
                "Daily Volatility Jump Frequency"
                "<br><sup>"
                "Daily jump rate and trailing "
                "10-session weighted rate"
                "</sup>"
            ),
            x=0.04,
            font=dict(
                color=TEXT_COLOR,
                size=23,
            ),
        ),

        paper_bgcolor=BACKGROUND,
        plot_bgcolor=BACKGROUND,

        font=dict(
            family="Arial",
            color=TEXT_COLOR,
            size=13,
        ),

        xaxis=dict(
            title="Trading Date (UTC)",
            tickformat="%b %Y",
            dtick="M1",
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickfont=dict(color=MUTED_COLOR),
        ),

        yaxis=dict(
            title="Detected Jumps (% of Candles)",
            ticksuffix="%",
            rangemode="tozero",
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickfont=dict(color=MUTED_COLOR),
        ),

        legend=dict(
            orientation="h",
            x=0.02,
            y=1.04,
            font=dict(color=TEXT_COLOR),
        ),

        margin=dict(
            l=100,
            r=55,
            t=145,
            b=100,
        ),

        height=650,

        hovermode="x unified",

        hoverlabel=dict(
            bgcolor="#1E293B",
            font_color=TEXT_COLOR,
        ),
    )

    return fig
