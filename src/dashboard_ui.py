from __future__ import annotations

from pathlib import Path

import streamlit as st


def load_css(css_path: str | Path) -> None:
    """
    Load a CSS file into Streamlit.
    """

    css_path = Path(css_path)

    if not css_path.exists():
        return

    css = css_path.read_text(encoding="utf-8")

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )


def render_dashboard_card(
    title: str,
    body: str,
    icon: str = "📊",
    eyebrow: str | None = None,
) -> None:
    """
    Render a reusable dashboard card.
    """

    eyebrow_html = ""

    if eyebrow:
        eyebrow_html = f'<div class="dashboard-card-eyebrow">{eyebrow}</div>'

    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="dashboard-card-icon">{icon}</div>
            {eyebrow_html}
            <h3>{title}</h3>
            <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_card(
    label: str,
    value: str,
    note: str,
) -> None:
    """
    Render a small dashboard status card.
    """

    st.markdown(
        f"""
        <div class="dashboard-status-card">
            <div class="dashboard-status-label">{label}</div>
            <div class="dashboard-status-value">{value}</div>
            <div class="dashboard-status-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(
    title: str,
    subtitle: str,
) -> None:
    """
    Render a cleaner page header.
    """

    st.markdown(
        f"""
        <div class="dashboard-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()


def render_footer_note(text: str) -> None:
    """
    Render a small dashboard footer note.
    """

    st.markdown(
        f'<div class="dashboard-footer">{text}</div>',
        unsafe_allow_html=True,
    )


def render_dataframe_download_button(
    df,
    filename: str,
    label: str = "Download CSV",
    key: str | None = None,
) -> None:
    """
    Render a Streamlit CSV download button for a dataframe.
    """

    csv_data = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label=label,
        data=csv_data,
        file_name=filename,
        mime="text/csv",
        key=key,
    )


def render_mockup_kpi_card(
    title: str,
    value: str,
    note: str,
    icon: str = "📊",
) -> None:
    """
    Render a polished KPI card for dashboard pages.
    """

    st.markdown(
        f"""
        <div class="mockup-kpi-card">
            <div>
                <div class="mockup-kpi-title">{title}</div>
                <div class="mockup-kpi-value">{value}</div>
                <div class="mockup-kpi-note">{note}</div>
            </div>
            <div class="mockup-kpi-icon">{icon}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mockup_panel_header(
    title: str,
    subtitle: str | None = None,
) -> None:
    """
    Render a panel header that matches the dashboard mockup style.
    """

    subtitle_html = ""

    if subtitle:
        subtitle_html = f'<div class="mockup-panel-subtitle">{subtitle}</div>'

    st.markdown(
        f"""
        <div class="mockup-panel-header">
            <div class="mockup-panel-title">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mockup_news_item(
    title: str,
    description: str,
    timestamp: str,
    impact: str,
) -> None:
    """
    Render a compact related news/event item.
    """

    impact_class = "mockup-impact-medium"

    if impact.lower().startswith("high"):
        impact_class = "mockup-impact-high"

    st.markdown(
        f"""
        <div class="mockup-news-item">
            <div class="mockup-news-dot"></div>
            <div class="mockup-news-content">
                <div class="mockup-news-title">{title}</div>
                <div class="mockup-news-description">{description}</div>
            </div>
            <div class="mockup-news-meta">
                <div class="mockup-news-time">{timestamp}</div>
                <div class="{impact_class}">{impact}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_mockup_sidebar_section(title: str) -> None:
    """
    Render a small uppercase sidebar section label.
    """

    st.sidebar.markdown(
        f"""
        <div class="mockup-sidebar-section">
            {title}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mockup_sidebar_summary(
    total_rows: str,
    date_range: str,
    sessions: str,
    timezone: str,
) -> None:
    """
    Render a sidebar data summary card.
    """

    st.sidebar.markdown(
        f"""
        <div class="mockup-sidebar-summary">
            <div class="mockup-sidebar-summary-title">Data Summary</div>

            <div class="mockup-sidebar-summary-row">
                <span>Total Rows</span>
                <strong>{total_rows}</strong>
            </div>

            <div class="mockup-sidebar-summary-row">
                <span>Date Range</span>
                <strong>{date_range}</strong>
            </div>

            <div class="mockup-sidebar-summary-row">
                <span>Sessions</span>
                <strong>{sessions}</strong>
            </div>

            <div class="mockup-sidebar-summary-row">
                <span>Timezone</span>
                <strong>{timezone}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mockup_export_hint(text: str) -> None:
    """
    Render a compact export/status hint in the main page.
    """

    st.markdown(
        f"""
        <div class="mockup-export-hint">
            {text}
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_mockup_topbar(
    title: str,
    subtitle: str,
    status_text: str = "Last run: dashboard session",
    action_text: str = "Export-ready",
) -> None:
    """
    Render a mockup-style top bar with title, status, and action text.
    """

    html = (
        f'<div class="mockup-topbar">'
        f'<div>'
        f'<div class="mockup-topbar-title">{title}</div>'
        f'<div class="mockup-topbar-subtitle">{subtitle}</div>'
        f'</div>'
        f'<div class="mockup-topbar-actions">'
        f'<span>{status_text}</span>'
        f'<span class="mockup-refresh-pill">↻</span>'
        f'<span class="mockup-export-pill">{action_text}</span>'
        f'</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)

def apply_mockup_chart_layout(
    fig,
    height: int,
    xaxis_title: str,
    yaxis_title: str,
) -> None:
    """
    Apply consistent chart styling for mockup-style dashboard charts.
    """

    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=28, b=18),
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        zeroline=False,
    )

    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        zeroline=False,
    )

def render_mockup_table_toolbar(
    title: str,
    detail: str,
) -> None:
    """
    Render a compact toolbar above dashboard tables.
    """

    st.markdown(
        f"""
        <div class="mockup-table-toolbar">
            <div>
                <div class="mockup-table-toolbar-title">{title}</div>
                <div class="mockup-table-toolbar-detail">{detail}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )