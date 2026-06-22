from __future__ import annotations


THEME_OPTIONS = ["Light", "Dark", "Auto"]


def normalize_theme(theme: str | None) -> str:
    """
    Normalize the selected theme.
    """

    if theme is None:
        return "Light"

    theme = str(theme).strip().title()

    if theme not in THEME_OPTIONS:
        return "Light"

    return theme


def get_plotly_template(theme: str | None) -> str:
    """
    Return the Plotly template for the selected theme.
    """

    theme = normalize_theme(theme)

    if theme == "Dark":
        return "plotly_dark"

    return "plotly_white"


def get_theme_css(theme: str | None) -> str:
    """
    Return custom CSS for Streamlit light/dark mode.
    """

    theme = normalize_theme(theme)

    if theme == "Auto":
        return ""

    if theme == "Dark":
        return """
        <style>
        .stApp {
            background-color: #0f172a;
            color: #e5e7eb;
        }

        section[data-testid="stSidebar"] {
            background-color: #111827;
        }

        div[data-testid="stMetric"] {
            background-color: #111827;
            border: 1px solid #1f2937;
            padding: 1rem;
            border-radius: 0.75rem;
        }

        .stDataFrame {
            background-color: #111827;
        }
        </style>
        """

    return """
    <style>
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }

    section[data-testid="stSidebar"] {
        background-color: #ffffff;
    }

    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 1rem;
        border-radius: 0.75rem;
    }
    </style>
    """


def apply_streamlit_theme(theme: str | None) -> None:
    """
    Apply a light/dark theme to a Streamlit app.
    """

    import streamlit as st

    css = get_theme_css(theme)

    if css:
        st.markdown(css, unsafe_allow_html=True)