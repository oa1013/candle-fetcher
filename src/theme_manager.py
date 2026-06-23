from __future__ import annotations

import streamlit as st


THEME_OPTIONS = [
    "Auto",
    "Light",
    "Dark",
]

THEME_SESSION_KEY = "candle_dashboard_theme"


def initialize_theme_state(default_theme: str = "Auto") -> None:
    """
    Store the selected theme globally across Streamlit pages.
    """

    if THEME_SESSION_KEY not in st.session_state:
        st.session_state[THEME_SESSION_KEY] = default_theme


def render_theme_selector(label: str = "Theme") -> str:
    """
    Render one shared theme selector.

    Because every page uses the same session_state key, the selected theme
    stays the same while moving between dashboard pages.
    """

    initialize_theme_state()

    current_theme = st.session_state.get(THEME_SESSION_KEY, "Auto")

    if current_theme not in THEME_OPTIONS:
        current_theme = "Auto"
        st.session_state[THEME_SESSION_KEY] = current_theme

    selected_theme = st.sidebar.selectbox(
        label,
        THEME_OPTIONS,
        index=THEME_OPTIONS.index(current_theme),
        key=THEME_SESSION_KEY,
    )

    return selected_theme


def get_plotly_template(theme: str) -> str:
    """
    Return the matching Plotly template for the selected theme.
    """

    if theme == "Dark":
        return "plotly_dark"

    return "plotly_white"


def apply_streamlit_theme(theme: str) -> None:
    """
    Apply dashboard CSS theme styling.
    """

    if theme == "Dark":
        _apply_dark_theme()
        return

    if theme == "Light":
        _apply_light_theme()
        return

    _apply_auto_theme()


def _apply_dark_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --dashboard-bg: #0f172a;
            --dashboard-panel: #111827;
            --dashboard-panel-soft: #1f2937;
            --dashboard-sidebar: #111827;
            --dashboard-text: #f8fafc;
            --dashboard-muted: #cbd5e1;
            --dashboard-border: rgba(148, 163, 184, 0.28);
        }

        .stApp {
            background: var(--dashboard-bg);
            color: var(--dashboard-text);
        }

        section[data-testid="stSidebar"] {
            background: var(--dashboard-sidebar);
        }

        section[data-testid="stSidebar"] * {
            color: var(--dashboard-text);
        }

        .dashboard-card,
        .dashboard-panel {
            background: var(--dashboard-panel);
            border-color: var(--dashboard-border);
            color: var(--dashboard-text);
        }

        .dashboard-card p,
        .dashboard-muted,
        .dashboard-footer {
            color: var(--dashboard-muted);
        }

        div[data-testid="stMetric"] {
            background: var(--dashboard-panel);
            border: 1px solid var(--dashboard-border);
            border-radius: 1rem;
            padding: 1rem;
        }

        div[data-testid="stMetric"] * {
            color: var(--dashboard-text);
        }

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea {
            background-color: var(--dashboard-panel-soft) !important;
            color: var(--dashboard-text) !important;
            border-color: var(--dashboard-border) !important;
        }

        label,
        p,
        span,
        h1,
        h2,
        h3,
        h4 {
            color: var(--dashboard-text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _apply_light_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --dashboard-bg: #f8fafc;
            --dashboard-panel: #ffffff;
            --dashboard-panel-soft: #ffffff;
            --dashboard-sidebar: #f1f5f9;
            --dashboard-text: #0f172a;
            --dashboard-muted: #64748b;
            --dashboard-border: rgba(148, 163, 184, 0.32);
        }

        .stApp {
            background: var(--dashboard-bg);
            color: var(--dashboard-text);
        }

        section[data-testid="stSidebar"] {
            background: var(--dashboard-sidebar);
        }

        section[data-testid="stSidebar"] * {
            color: var(--dashboard-text);
        }

        .dashboard-card,
        .dashboard-panel {
            background: var(--dashboard-panel);
            border-color: var(--dashboard-border);
            color: var(--dashboard-text);
        }

        .dashboard-card p,
        .dashboard-muted,
        .dashboard-footer {
            color: var(--dashboard-muted);
        }

        div[data-testid="stMetric"] {
            background: var(--dashboard-panel);
            border: 1px solid var(--dashboard-border);
            border-radius: 1rem;
            padding: 1rem;
        }

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea {
            background-color: var(--dashboard-panel-soft) !important;
            color: var(--dashboard-text) !important;
            border-color: var(--dashboard-border) !important;
        }

        label,
        p,
        span,
        h1,
        h2,
        h3,
        h4 {
            color: var(--dashboard-text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _apply_auto_theme() -> None:
    st.markdown(
        """
        <style>
        @media (prefers-color-scheme: dark) {
            :root {
                --dashboard-bg: #0f172a;
                --dashboard-panel: #111827;
                --dashboard-panel-soft: #1f2937;
                --dashboard-sidebar: #111827;
                --dashboard-text: #f8fafc;
                --dashboard-muted: #cbd5e1;
                --dashboard-border: rgba(148, 163, 184, 0.28);
            }
        }

        @media (prefers-color-scheme: light) {
            :root {
                --dashboard-bg: #f8fafc;
                --dashboard-panel: #ffffff;
                --dashboard-panel-soft: #ffffff;
                --dashboard-sidebar: #f1f5f9;
                --dashboard-text: #0f172a;
                --dashboard-muted: #64748b;
                --dashboard-border: rgba(148, 163, 184, 0.32);
            }
        }

        .stApp {
            background: var(--dashboard-bg);
            color: var(--dashboard-text);
        }

        section[data-testid="stSidebar"] {
            background: var(--dashboard-sidebar);
        }

        section[data-testid="stSidebar"] * {
            color: var(--dashboard-text);
        }

        .dashboard-card,
        .dashboard-panel {
            background: var(--dashboard-panel);
            border-color: var(--dashboard-border);
            color: var(--dashboard-text);
        }

        .dashboard-card p,
        .dashboard-muted,
        .dashboard-footer {
            color: var(--dashboard-muted);
        }

        div[data-testid="stMetric"] {
            background: var(--dashboard-panel);
            border: 1px solid var(--dashboard-border);
            border-radius: 1rem;
            padding: 1rem;
        }

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea {
            background-color: var(--dashboard-panel-soft) !important;
            color: var(--dashboard-text) !important;
            border-color: var(--dashboard-border) !important;
        }

        label,
        p,
        span,
        h1,
        h2,
        h3,
        h4 {
            color: var(--dashboard-text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )