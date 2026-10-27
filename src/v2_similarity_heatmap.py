from __future__ import annotations

import math

import plotly.graph_objects as go


# --------------------------------------------------
# Candle Fetcher 2.0 — Similarity heatmap
# --------------------------------------------------

BACKGROUND = "#0F1724"
TEXT_COLOR = "#E5EDF7"
MUTED_COLOR = "#94A3B8"
DIAGONAL_COLOR = "#1E293B"


def build_metric_similarity_heatmap(result: dict) -> go.Figure:
    """
    Create a professional metric similarity heatmap.

    Similarity values come directly from the original
    CSV Comparison engine.

    Self-comparison cells remain unavailable (N/A).
    No correlations or similarity scores are invented.
    """

    labels = list(result["dataset_labels"])
    comparisons = result["raw_result"]["pairwise_comparisons"]

    if len(labels) < 2:
        raise ValueError("At least two datasets are required.")

    if len(labels) != len(set(labels)):
        raise ValueError("Dataset labels must be unique.")

    required_columns = {
        "label_a",
        "label_b",
        "metric_similarity_pct",
        "overlap_rows",
    }

    missing = required_columns - set(comparisons.columns)

    if missing:
        raise ValueError(
            f"Missing comparison columns: {sorted(missing)}"
        )

    count = len(labels)

    # Short labels for chart axes only.
    # Full dataset labels are retained in the data and hover text.
    session_names = [
        label.split(" | ", 1)[0]
        for label in labels
    ]

    short_labels = []

    for index, (full_label, session) in enumerate(
        zip(labels, session_names)
    ):
        if session_names.count(session) == 1:
            candidate = session
        else:
            suffix = full_label.rsplit(" | ", 1)[-1]
            candidate = f"{session} | {suffix}"

        if candidate in short_labels:
            candidate = f"{session} #{index + 1}"

        short_labels.append(candidate)

    positions = {
        label: index
        for index, label in enumerate(labels)
    }

    # No self-comparison values are supplied by the engine.
    matrix = [
        [None for _ in range(count)]
        for _ in range(count)
    ]

    cell_text = [
        ["" for _ in range(count)]
        for _ in range(count)
    ]

    hover_text = [
        ["" for _ in range(count)]
        for _ in range(count)
    ]

    # --------------------------------------------------
    # Populate values from the original engine
    # --------------------------------------------------

    for row in comparisons.to_dict("records"):

        label_a = str(row["label_a"])
        label_b = str(row["label_b"])

        if label_a not in positions or label_b not in positions:
            raise ValueError("Unexpected comparison dataset label.")

        similarity = float(row["metric_similarity_pct"])

        if not math.isfinite(similarity):
            raise ValueError("Similarity score must be finite.")

        if not 0 <= similarity <= 100:
            raise ValueError("Similarity score must be between 0 and 100.")

        overlap = int(row["overlap_rows"])

        if overlap < 0:
            raise ValueError("Overlap count cannot be negative.")

        i = positions[label_a]
        j = positions[label_b]

        if i == j:
            continue

        description = (
            f"<b>{label_a} vs {label_b}</b>"
            f"<br>Metric similarity: {similarity:.2f}%"
            f"<br>Overlapping candles: {overlap}"
            "<br>Not a return correlation"
        )

        matrix[i][j] = similarity
        matrix[j][i] = similarity

        cell_text[i][j] = f"{similarity:.1f}%"
        cell_text[j][i] = f"{similarity:.1f}%"

        hover_text[i][j] = description
        hover_text[j][i] = description

    # --------------------------------------------------
    # Plotly heatmap
    # --------------------------------------------------

    fig = go.Figure()

    fig.add_trace(
        go.Heatmap(
            z=matrix,
            x=labels,
            y=labels,
            zmin=0,
            zmax=100,
            colorscale=[
                [0.00, "#1E3A8A"],  # Low: deep blue
                [0.25, "#2563EB"],  # Blue
                [0.45, "#22D3EE"],  # Cyan
                [0.60, "#FACC15"],  # Yellow
                [0.78, "#F97316"],  # Orange
                [1.00, "#DC2626"],  # High: red
            ],
            xgap=6,
            ygap=6,
            text=cell_text,
            # Cell annotations provide contrast-aware labels.

            customdata=hover_text,
            hovertemplate="%{customdata}<extra></extra>",
            hoverongaps=False,
            colorbar=dict(
                title=dict(text="Similarity %"),
                thickness=16,
                len=0.75,
                tickvals=[0, 25, 50, 75, 100],
                ticksuffix="%",
                outlinewidth=0,
                tickfont=dict(color=TEXT_COLOR),
            ),
        )
    )

    # --------------------------------------------------
    # Display unavailable self-comparison cells
    # --------------------------------------------------

    # Labels use contrasting text depending on cell colour.
    for row_index, row_label in enumerate(labels):
        for col_index, col_label in enumerate(labels):
            score = matrix[row_index][col_index]

            if score is None:
                continue

            label_color = (
                "#F8FAFC"
                if score < 40 or score >= 90
                else "#0F1724"
            )

            fig.add_annotation(
                x=col_label,
                y=row_label,
                text=f"{score:.1f}%",
                showarrow=False,
                font=dict(
                    color=label_color,
                    size=17,
                ),
            )

    for index, label in enumerate(labels):

        # Categorical positions correspond to 0, 1, 2...
        # These shapes only provide a visual background.
        # They do not create statistical observations.
        fig.add_shape(
            type="rect",
            xref="x",
            yref="y",
            x0=index - 0.49,
            x1=index + 0.49,
            y0=index - 0.49,
            y1=index + 0.49,
            fillcolor=DIAGONAL_COLOR,
            line=dict(
                color="#334155",
                width=1,
            ),
            layer="above",
        )

        fig.add_annotation(
            x=label,
            y=label,
            text="N/A",
            showarrow=False,
            font=dict(
                color=MUTED_COLOR,
                size=16,
            ),
        )

    # --------------------------------------------------
    # Premium dashboard styling
    # --------------------------------------------------

    fig.update_layout(
        title=dict(
            text=(
                "Dataset Metric Similarity"
                "<br><sup>"
                "Metric-based similarity — not return correlation"
                "</sup>"
            ),
            font=dict(
                size=22,
                color=TEXT_COLOR,
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
            title="Dataset",
            type="category",
            categoryorder="array",
            categoryarray=labels,
            tickmode="array",
            tickvals=labels,
            ticktext=short_labels,
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            tickangle=-30 if count > 4 else 0,
            tickfont=dict(
                size=13,
                color=TEXT_COLOR,
            ),
        ),
        yaxis=dict(
            title="Dataset",
            type="category",
            categoryorder="array",
            categoryarray=labels,
            tickmode="array",
            tickvals=labels,
            ticktext=short_labels,
            autorange="reversed",
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks="",
            scaleanchor="x",
            scaleratio=1,
            tickfont=dict(
                size=13,
                color=TEXT_COLOR,
            ),
        ),
        margin=dict(
            l=125,
            r=110,
            t=125,
            b=110,
        ),
        height=max(600, min(1000, 160 * count + 280)),
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_color=TEXT_COLOR,
        ),
    )

    return fig
