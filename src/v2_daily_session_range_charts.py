from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go


# ------------------------------------------
# Candle Fetcher 2.0 chart colours
# ------------------------------------------

BACKGROUND = "#0F1724"
TEXT_COLOR = "#E5EDF7"
MUTED_COLOR = "#94A3B8"
GRID_COLOR = "#273449"

BLUE = "#2563EB"
CYAN = "#22D3EE"
ORANGE = "#F97316"
YELLOW = "#FACC15"


def build_daily_range_chart(result: dict) -> go.Figure:
    """
    Visualise historical daily high-to-low ranges.

    Uses the existing range-analysis engine.

    Daily timestamps are UTC.
    The reference median uses reference-coverage
    trading days only.
    """

    if result.get("status") != "completed":
        raise ValueError(
            "A completed range-analysis result is required."
        )

    daily = result["daily_ranges"].copy()

    required_columns = {
        "trading_date",
        "high",
        "low",
        "range_points",
        "range_percent",
        "candle_count",
        "coverage_status",
    }

    missing = required_columns - set(daily.columns)

    if missing:
        raise ValueError(
            f"Missing daily range columns: {sorted(missing)}"
        )

    if daily.empty:
        raise ValueError(
            "No historical daily ranges are available."
        )

    # ------------------------------------------
    # Validate underlying data
    # ------------------------------------------

    dates = pd.to_datetime(
        daily["trading_date"],
        utc=True,
        errors="raise",
    )

    if dates.isna().any():
        raise ValueError("Invalid trading dates.")

    if dates.duplicated().any():
        raise ValueError("Duplicate trading dates.")

    if not dates.is_monotonic_increasing:
        raise ValueError(
            "Trading dates must be chronological."
        )

    numeric_columns = [
        "high",
        "low",
        "range_points",
        "range_percent",
        "candle_count",
    ]

    for column in numeric_columns:
        daily[column] = pd.to_numeric(
            daily[column],
            errors="raise",
        )

        if not all(
            math.isfinite(float(value))
            for value in daily[column]
        ):
            raise ValueError(
                f"Invalid numeric values in {column}."
            )

    if (daily["candle_count"] <= 0).any():
        raise ValueError(
            "Daily candle counts must be positive."
        )

    if (
        (daily["low"] <= 0)
        | (daily["high"] < daily["low"])
        | (daily["range_points"] < 0)
    ).any():
        raise ValueError(
            "Invalid daily high, low or range."
        )

    if int(daily["candle_count"].sum()) != int(
        result["total_candles"]
    ):
        raise ValueError(
            "Daily candle totals do not match the analysis."
        )

    expected_ranges = (
        daily["high"] - daily["low"]
    ).round(2)

    if not all(
        math.isclose(
            float(actual),
            float(expected),
            rel_tol=0,
            abs_tol=0.011,
        )
        for actual, expected in zip(
            daily["range_points"],
            expected_ranges,
        )
    ):
        raise ValueError(
            "Daily ranges do not match high minus low."
        )

    # ------------------------------------------
    # Full-coverage reference median
    # ------------------------------------------

    reference = daily[
        daily["coverage_status"] == "reference_coverage"
    ]

    reference_median = (
        float(reference["range_points"].median())
        if not reference.empty
        else None
    )

    # ------------------------------------------
    # Interactive daily range chart
    # ------------------------------------------

    custom_data = list(
        zip(
            daily["high"],
            daily["low"],
            daily["range_percent"],
            daily["candle_count"],
            daily["coverage_status"],
        )
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=daily["range_points"],
            mode="lines+markers",
            name="Daily range",
            line=dict(
                color=BLUE,
                width=2,
            ),
            marker=dict(
                color=BLUE,
                size=5,
            ),
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.09)",
            customdata=custom_data,
            hovertemplate=(
                "<b>%{x|%Y-%m-%d} UTC</b>"
                "<br>Daily range: %{y:.2f} points"
                "<br>High: %{customdata[0]:,.2f}"
                "<br>Low: %{customdata[1]:,.2f}"
                "<br>Range: %{customdata[2]:.3f}%"
                "<br>Candles: %{customdata[3]}"
                "<br>Coverage: %{customdata[4]}"
                "<extra></extra>"
            ),
        )
    )

    # ------------------------------------------
    # Mark reduced-coverage days
    # ------------------------------------------

    reduced_mask = (
        daily["coverage_status"] == "reduced_coverage"
    )

    if reduced_mask.any():

        fig.add_trace(
            go.Scatter(
                x=dates[reduced_mask],
                y=daily.loc[
                    reduced_mask, "range_points"
                ],
                mode="markers",
                name="Reduced coverage",
                marker=dict(
                    color=ORANGE,
                    size=10,
                    symbol="diamond",
                    line=dict(
                        color=BACKGROUND,
                        width=1,
                    ),
                ),
                hovertemplate=(
                    "<b>%{x|%Y-%m-%d} UTC</b>"
                    "<br>Range: %{y:.2f} points"
                    "<br>Reduced candle coverage"
                    "<extra></extra>"
                ),
            )
        )

    # ------------------------------------------
    # Mark above-reference coverage
    # ------------------------------------------

    above_mask = (
        daily["coverage_status"] == "above_reference"
    )

    if above_mask.any():

        fig.add_trace(
            go.Scatter(
                x=dates[above_mask],
                y=daily.loc[
                    above_mask, "range_points"
                ],
                mode="markers",
                name="Above-reference coverage",
                marker=dict(
                    color=YELLOW,
                    size=10,
                    symbol="diamond",
                ),
                hovertemplate=(
                    "<b>%{x|%Y-%m-%d} UTC</b>"
                    "<br>Range: %{y:.2f} points"
                    "<br>Above-reference candle coverage"
                    "<extra></extra>"
                ),
            )
        )

    # ------------------------------------------
    # Reference median
    # ------------------------------------------

    if reference_median is not None:

        fig.add_hline(
            y=reference_median,
            line_color=CYAN,
            line_dash="dash",
            line_width=2,
            annotation_text=(
                f"Reference median: {reference_median:.2f}"
            ),
            annotation_position="top right",
            annotation_font_color=CYAN,
        )

    # ------------------------------------------
    # Premium dark styling
    # ------------------------------------------

    fig.update_layout(
        title=dict(
            text=(
                "Historical Daily High-to-Low Ranges"
                "<br><sup>"
                "Daily price movement in Nasdaq points — UTC"
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
            title="High-to-Low Range (Points)",
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
            l=110,
            r=70,
            t=145,
            b=100,
        ),

        height=650,

        hovermode="closest",

        hoverlabel=dict(
            bgcolor="#1E293B",
            font_color=TEXT_COLOR,
        ),
    )

    return fig


def build_session_range_comparison_chart(
    result: dict,
) -> go.Figure:
    """
    Compare historical session range distributions.

    Only sessions passing the original coverage
    validation are included in the box plots.

    Range measurements come from the existing
    range analysis engine.
    """

    if result.get("status") != "completed":
        raise ValueError(
            "A completed range-analysis result is required."
        )

    session_ranges = result["session_ranges"]
    summaries = result["session_summaries"]

    sessions = [
        ("new_york", "New York", "#2563EB",
         "rgba(37,99,235,0.30)"),
        ("london", "London", "#22D3EE",
         "rgba(34,211,238,0.25)"),
        ("asia", "Asia", "#A78BFA",
         "rgba(167,139,250,0.28)"),
    ]

    fig = go.Figure()
    total_complete = 0

    # ------------------------------------------
    # Build each session distribution
    # ------------------------------------------

    for key, label, color, fill_color in sessions:

        if key not in session_ranges or key not in summaries:
            raise ValueError(
                f"Missing session results: {key}"
            )

        data = session_ranges[key]
        summary = summaries[key]

        required_columns = {
            "range_points",
            "is_complete",
            "candle_count",
        }

        missing = required_columns - set(data.columns)

        if missing:
            raise ValueError(
                f"Missing {label} columns: {sorted(missing)}"
            )

        complete = data.loc[
            data["is_complete"]
            .fillna(False)
            .astype(bool)
        ].copy()

        if len(data) != summary["total_sessions"]:
            raise ValueError(
                f"{label} session totals do not match."
            )

        if len(complete) != summary["complete_sessions"]:
            raise ValueError(
                f"{label} complete-session count does not match."
            )

        if complete.empty:
            continue

        values = pd.to_numeric(
            complete["range_points"],
            errors="raise",
        ).astype(float)

        if not all(
            math.isfinite(float(value))
            for value in values
        ):
            raise ValueError(
                f"{label} contains invalid ranges."
            )

        if (values < 0).any():
            raise ValueError(
                f"{label} contains negative ranges."
            )

        actual_median = round(
            float(values.median()), 2
        )

        if not math.isclose(
            actual_median,
            float(summary["median_range"]),
            rel_tol=0,
            abs_tol=0.011,
        ):
            raise ValueError(
                f"{label} median does not match the engine."
            )

        total_complete += len(complete)

        fig.add_trace(
            go.Box(
                x=values.tolist(),
                name=f"{label} (n={len(complete)})",
                orientation="h",
                quartilemethod="linear",
                boxpoints="outliers",
                line=dict(
                    color=color,
                    width=2,
                ),
                marker=dict(
                    color=color,
                    size=6,
                    opacity=0.85,
                ),
                fillcolor=fill_color,
                whiskerwidth=0.6,
                showlegend=False,
            )
        )

    if total_complete == 0:
        raise ValueError(
            "No complete sessions are available "
            "for a meaningful comparison."
        )

    # ------------------------------------------
    # Premium dark chart styling
    # ------------------------------------------

    fig.update_layout(
        title=dict(
            text=(
                "Historical Session Range Distributions"
                "<br><sup>"
                "Complete sessions only — "
                "New York, London and Asia"
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
            title="Session High-to-Low Range (Nasdaq Points)",
            rangemode="tozero",
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickfont=dict(color=MUTED_COLOR),
        ),

        yaxis=dict(
            title="Trading Session",
            autorange="reversed",
            showgrid=False,
            zeroline=False,
            tickfont=dict(
                color=TEXT_COLOR,
                size=14,
            ),
        ),

        margin=dict(
            l=190,
            r=65,
            t=140,
            b=95,
        ),

        height=570,

        hoverlabel=dict(
            bgcolor="#1E293B",
            font_color=TEXT_COLOR,
        ),

        showlegend=False,
    )

    return fig
