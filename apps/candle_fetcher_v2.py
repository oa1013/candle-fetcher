
from __future__ import annotations

import streamlit as st


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Candle Fetcher 2.0",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# Dark theme styling
# --------------------------------------------------

st.markdown(
    """
    <style>

    /* -----------------------------------------
       Main Application
    ----------------------------------------- */

    /* Hide original Streamlit page navigation */
    [data-testid="stSidebarNav"] {
        display: none;
    }

    /* Main application background */
    .stApp {
        background-color: #0F1724;
        color: #E5EDF7;
    }

    /* Main content container */
    .block-container,
    [data-testid="stMainBlockContainer"] {
        max-width: 1600px;
        padding-top: 5rem !important;
        padding-bottom: 2rem;
    }

    /* Match the Streamlit top header to our dark theme */
    [data-testid="stHeader"],
    .stAppHeader {
        background-color: #0F1724 !important;
    }

    /* Headings */
    h1, h2, h3 {
        color: #F3F6FC;
        font-weight: 600;
    }

    /* Dividers */
    hr {
        border-color: #273449;
    }


    /* -----------------------------------------
       Sidebar Appearance
    ----------------------------------------- */

    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: #151F2E;
        border-right: 1px solid #273449;
    }

    /* Increase sidebar width */
    [data-testid="stSidebar"][aria-expanded="true"] {
        min-width: 290px !important;
        width: 290px !important;
        max-width: 290px !important;
    }

    /* Set inner sidebar width */
    [data-testid="stSidebar"] > div:first-child {
        width: 290px !important;
    }

    /* Reduce vertical spacing */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.45rem;
    }

    /* Sidebar headings */
    [data-testid="stSidebar"] h2 {
        font-size: 1.15rem;
        font-weight: 700;
        color: #F3F6FC;
    }

    [data-testid="stSidebar"] h5 {
        font-size: 0.78rem;
        font-weight: 700;
        color: #94A3B8;
        letter-spacing: 0.06em;
    }

    /* Sidebar caption */
    [data-testid="stSidebar"] .stCaption {
        color: #94A3B8;
        font-size: 0.75rem;
    }


    /* -----------------------------------------
       Sidebar Navigation Buttons
    ----------------------------------------- */

    /* Default navigation buttons */
    [data-testid="stSidebar"] .stButton button {
        background-color: transparent;
        color: #CBD5E1;
        border: 1px solid transparent;
        border-radius: 8px;

        width: 100%;
        min-height: 38px;
        padding: 0.45rem 0.75rem;

        text-align: left;
        justify-content: flex-start;

        font-size: 0.85rem;
        font-weight: 500;

        transition:
            background-color 0.15s ease,
            border-color 0.15s ease,
            color 0.15s ease;
    }

    /* Navigation button text */
    [data-testid="stSidebar"] .stButton button p {
        font-size: 0.85rem;
        line-height: 1.3;
        text-align: left;
        white-space: normal;
        overflow-wrap: break-word;
    }

    /* Hover effect */
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #1E3048;
        color: #FFFFFF;
        border-color: #334155;
    }

    /* Selected navigation button */
    [data-testid="stSidebar"]
    .stButton button[data-testid="stBaseButton-primary"] {
        background-color: #2563EB;
        color: #FFFFFF;
        border-color: #2563EB;
        font-weight: 600;
    }

    /* Selected button hover */
    [data-testid="stSidebar"]
    .stButton button[data-testid="stBaseButton-primary"]:hover {
        background-color: #1D4ED8;
        color: #FFFFFF;
        border-color: #1D4ED8;
    }

    /* Selected button text */
    [data-testid="stSidebar"]
    .stButton button[data-testid="stBaseButton-primary"] p {
        color: #FFFFFF;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Sidebar navigation
# --------------------------------------------------

RUNNERS = [
    "New York Runner",
    "London Runner",
    "Asia Runner",
    "All Sessions Runner",
    "CSV Comparison Runner",
    "Period Regime Finder",
    "Volatility Jump Runner",
    "Daily Session Range Analyzer",
]

SYSTEM_PAGES = [
    "Settings",
    "Environment",
    "Working Directory",
    "Logs",
    "Help",
]


# --------------------------------------------------
# Session state
# --------------------------------------------------

# Remember the selected page.
if "selected_page" not in st.session_state:
    st.session_state.selected_page = "New York Runner"


# --------------------------------------------------
# Sidebar layout
# --------------------------------------------------

with st.sidebar:

    # Application branding
    st.markdown("## CANDLE FETCHER")
    st.caption("Version 2.0")

    st.divider()

    # ------------------------------------------
    # Runners
    # ------------------------------------------

    st.markdown("##### RUNNERS")

    for runner in RUNNERS:

        is_selected = (
            st.session_state.selected_page == runner
        )

        if st.button(
            runner,
            key=f"runner_{runner}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state.selected_page = runner
            st.rerun()

    st.divider()

    # ------------------------------------------
    # System
    # ------------------------------------------

    st.markdown("##### SYSTEM")

    for page in SYSTEM_PAGES:

        is_selected = (
            st.session_state.selected_page == page
        )

        if st.button(
            page,
            key=f"system_{page}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state.selected_page = page
            st.rerun()


# --------------------------------------------------
# Main workspace
# --------------------------------------------------

selected_page = st.session_state.selected_page

st.caption("CANDLE FETCHER / WORKSPACE")

st.title(selected_page)

st.divider()


# --------------------------------------------------
# Runner workspace
# --------------------------------------------------

if selected_page in RUNNERS:

    st.subheader("Runner Workspace")

    st.info(
        f"{selected_page} selected. "
        "Runner configuration and execution controls "
        "will be added in the next development stages."
    )


# --------------------------------------------------
# System workspace
# --------------------------------------------------

else:

    st.subheader("System Workspace")

    st.info(
        f"{selected_page} selected. "
        "System settings and tools will be added later."
    )
