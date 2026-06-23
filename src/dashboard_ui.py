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
) -> None:
    """
    Render a reusable dashboard card.
    """

    st.markdown(
        f"""
        <div class="dashboard-card">
            <h3>{title}</h3>
            <p>{body}</p>
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

    st.title(title)
    st.markdown(
        f'<p class="dashboard-muted">{subtitle}</p>',
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