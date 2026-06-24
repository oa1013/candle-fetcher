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