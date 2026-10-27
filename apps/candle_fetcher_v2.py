
from __future__ import annotations

import streamlit as st

# --------------------------------------------------
# Candle Fetcher 2.0 — Runner integrations
# --------------------------------------------------

from src.v2_runner_integration import (
    run_new_york_v2,
    run_london_v2,
    run_asia_v2,
)

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


    /* -----------------------------------------
       Main Workspace Primary Buttons
    ----------------------------------------- */

    /* Electric-blue primary buttons */
    [data-testid="stMainBlockContainer"]
    .stButton button[data-testid="stBaseButton-primary"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border-color: #2563EB !important;
    }

    /* Darker blue when hovering */
    [data-testid="stMainBlockContainer"]
    .stButton button[data-testid="stBaseButton-primary"]:hover {
        background-color: #1D4ED8 !important;
        color: #FFFFFF !important;
        border-color: #1D4ED8 !important;
    }

    /* Keep primary button text white */
    [data-testid="stMainBlockContainer"]
    .stButton button[data-testid="stBaseButton-primary"] p {
        color: #FFFFFF !important;
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

    # Main workspace and right-side status panel
    workspace_col, status_col = st.columns(
        [3, 1],
        gap="large",
    )

    # ------------------------------------------
    # Main runner configuration
    # ------------------------------------------

    with workspace_col:

        with st.container(border=True):

            st.subheader("Runner Configuration")

            st.caption(
                f"Configure and execute {selected_page}."
            )

            # ----------------------------------
            # New York Runner controls
            # ----------------------------------

            if selected_page == "New York Runner":

                symbol = st.text_input(
                    "MT5 Instrument",
                    value="US100.cash",
                    key="ny_symbol",
                )

                start_col, end_col = st.columns(2)

                with start_col:

                    start_date = st.date_input(
                        "Start Date",
                        key="ny_start_date",
                    )

                with end_col:

                    end_date = st.date_input(
                        "End Date",
                        key="ny_end_date",
                    )

                st.caption(
                    "Timeframe: M1 (1-minute candles)"
                )

                # ----------------------------------
                # Date validation
                # ----------------------------------

                if start_date > end_date:

                    st.error(
                        "Start Date must be on or before End Date."
                    )

                # ----------------------------------
                # Instrument validation
                # ----------------------------------

                if not symbol.strip():

                    st.error(
                        "MT5 Instrument cannot be empty."
                    )

                # ----------------------------------
                # Execution controls
                # ----------------------------------

                st.divider()

                st.markdown("#### Execution")

                configuration_valid = (
                    bool(symbol.strip())
                    and start_date <= end_date
                )

                if st.button(
                    "Validate Configuration",
                    key="ny_validate_configuration",
                    type="primary",
                    use_container_width=True,
                    disabled=not configuration_valid,
                ):

                    st.success(
                        "Configuration is valid. "
                        "Ready for MT5 integration."
                    )

                # ----------------------------------
                # Live New York Runner execution
                # ----------------------------------

                st.divider()

                if st.button(
                    "Run New York Runner",
                    key="ny_run_live",
                    type="primary",
                    use_container_width=True,
                    disabled=not configuration_valid,
                ):

                    # Clear the previous result before starting.
                    st.session_state["ny_last_result"] = None

                    try:

                        with st.spinner(
                            "Fetching MT5 candles and "
                            "processing the New York session..."
                        ):

                            result = run_new_york_v2(
                                symbol=symbol.strip(),
                                start_date=start_date,
                                end_date=end_date,
                            )

                        # Store results for the dashboard.
                        st.session_state["ny_last_result"] = result

                        # ----------------------------------
                        # Recent successful runs
                        # ----------------------------------

                        recent_runs = st.session_state.setdefault(
                            "ny_recent_runs", []
                        )

                        recent_runs.insert(
                            0,
                            {
                                "run_id": result["run_id"],
                                "symbol": result["symbol"],
                                "start_date": result["start_date"],
                                "end_date": result["end_date"],
                                "candles": result["session"]["final_rows"],
                                "export_path": result["session"]["export"]["output_path"],
                            },
                        )

                        # Keep only the five latest successful runs.
                        del recent_runs[5:]

                    except Exception as exc:

                        st.error(
                            f"New York Runner failed: {exc}"
                        )

                # ----------------------------------
                # Display successful execution
                # ----------------------------------

                last_result = st.session_state.get(
                    "ny_last_result"
                )

                if last_result is not None:

                    session_rows = last_result[
                        "session"
                    ]["final_rows"]

                    st.success(
                        "New York Runner completed successfully! "
                        f"{session_rows:,} session candles exported."
                    )

                    # ----------------------------------
                    # Download exported New York CSV
                    # ----------------------------------

                    export_info = last_result["session"]["export"]

                    try:
                        with open(export_info["output_path"], "rb") as csv_file:
                            csv_data = csv_file.read()

                    except OSError as exc:
                        st.error(
                            f"Could not prepare the CSV download: {exc}"
                        )

                    else:
                        st.download_button(
                            label="Download New York CSV",
                            data=csv_data,
                            file_name=export_info["filename"],
                            mime="text/csv",
                            key="ny_download_csv",
                            use_container_width=True,
                        )

            # ----------------------------------
            # London Runner controls
            # ----------------------------------

            elif selected_page == "London Runner":

                symbol = st.text_input(
                    "MT5 Instrument",
                    value="US100.cash",
                    key="london_symbol",
                )

                start_col, end_col = st.columns(2)

                with start_col:

                    start_date = st.date_input(
                        "Start Date",
                        key="london_start_date",
                    )

                with end_col:

                    end_date = st.date_input(
                        "End Date",
                        key="london_end_date",
                    )

                st.caption("Session: 08:00–11:00 (Europe/London)")

                st.caption(
                    "Timeframe: M1 (1-minute candles)"
                )

                # ----------------------------------
                # Date validation
                # ----------------------------------

                if start_date > end_date:

                    st.error(
                        "Start Date must be on or before End Date."
                    )

                # ----------------------------------
                # Instrument validation
                # ----------------------------------

                if not symbol.strip():

                    st.error(
                        "MT5 Instrument cannot be empty."
                    )

                # ----------------------------------
                # Execution controls
                # ----------------------------------

                st.divider()

                st.markdown("#### Execution")

                configuration_valid = (
                    bool(symbol.strip())
                    and start_date <= end_date
                )

                if st.button(
                    "Validate Configuration",
                    key="london_validate_configuration",
                    type="primary",
                    use_container_width=True,
                    disabled=not configuration_valid,
                ):

                    st.success(
                        "Configuration is valid. "
                        "Ready for MT5 integration."
                    )

                # ----------------------------------
                # Live London Runner execution
                # ----------------------------------

                st.divider()

                if st.button(
                    "Run London Runner",
                    key="london_run_live",
                    type="primary",
                    use_container_width=True,
                    disabled=not configuration_valid,
                ):

                    # Clear the previous result before starting.
                    st.session_state["london_last_result"] = None

                    try:

                        with st.spinner(
                            "Fetching MT5 candles and "
                            "processing the London session..."
                        ):

                            result = run_london_v2(
                                symbol=symbol.strip(),
                                start_date=start_date,
                                end_date=end_date,
                            )

                        # Store results for the dashboard.
                        st.session_state["london_last_result"] = result

                        # ----------------------------------
                        # Recent successful runs
                        # ----------------------------------

                        recent_runs = st.session_state.setdefault(
                            "london_recent_runs", []
                        )

                        recent_runs.insert(
                            0,
                            {
                                "run_id": result["run_id"],
                                "symbol": result["symbol"],
                                "start_date": result["start_date"],
                                "end_date": result["end_date"],
                                "candles": result["session"]["final_rows"],
                                "export_path": result["session"]["export"]["output_path"],
                            },
                        )

                        # Keep only the five latest successful runs.
                        del recent_runs[5:]

                    except Exception as exc:

                        st.error(
                            f"London Runner failed: {exc}"
                        )

                # ----------------------------------
                # Display successful execution
                # ----------------------------------

                last_result = st.session_state.get(
                    "london_last_result"
                )

                if last_result is not None:

                    session_rows = last_result[
                        "session"
                    ]["final_rows"]

                    st.success(
                        "London Runner completed successfully! "
                        f"{session_rows:,} session candles exported."
                    )

                    # ----------------------------------
                    # Download exported London CSV
                    # ----------------------------------

                    export_info = last_result["session"]["export"]

                    try:
                        with open(export_info["output_path"], "rb") as csv_file:
                            csv_data = csv_file.read()

                    except OSError as exc:
                        st.error(
                            f"Could not prepare the CSV download: {exc}"
                        )

                    else:
                        st.download_button(
                            label="Download London CSV",
                            data=csv_data,
                            file_name=export_info["filename"],
                            mime="text/csv",
                            key="london_download_csv",
                            use_container_width=True,
                        )

            # ----------------------------------
            # Asia Runner controls
            # ----------------------------------

            elif selected_page == "Asia Runner":

                symbol = st.text_input(
                    "MT5 Instrument",
                    value="US100.cash",
                    key="asia_symbol",
                )

                start_col, end_col = st.columns(2)

                with start_col:

                    start_date = st.date_input(
                        "Start Date",
                        key="asia_start_date",
                    )

                with end_col:

                    end_date = st.date_input(
                        "End Date",
                        key="asia_end_date",
                    )

                st.caption("Session: 09:00–12:00 (Asia/Tokyo)")

                st.caption(
                    "Timeframe: M1 (1-minute candles)"
                )

                # ----------------------------------
                # Date validation
                # ----------------------------------

                if start_date > end_date:

                    st.error(
                        "Start Date must be on or before End Date."
                    )

                # ----------------------------------
                # Instrument validation
                # ----------------------------------

                if not symbol.strip():

                    st.error(
                        "MT5 Instrument cannot be empty."
                    )

                # ----------------------------------
                # Execution controls
                # ----------------------------------

                st.divider()

                st.markdown("#### Execution")

                configuration_valid = (
                    bool(symbol.strip())
                    and start_date <= end_date
                )

                if st.button(
                    "Validate Configuration",
                    key="asia_validate_configuration",
                    type="primary",
                    use_container_width=True,
                    disabled=not configuration_valid,
                ):

                    st.success(
                        "Configuration is valid. "
                        "Ready for MT5 integration."
                    )

                # ----------------------------------
                # Live Asia Runner execution
                # ----------------------------------

                st.divider()

                if st.button(
                    "Run Asia Runner",
                    key="asia_run_live",
                    type="primary",
                    use_container_width=True,
                    disabled=not configuration_valid,
                ):

                    # Clear the previous result before starting.
                    st.session_state["asia_last_result"] = None

                    try:

                        with st.spinner(
                            "Fetching MT5 candles and "
                            "processing the Asia session..."
                        ):

                            result = run_asia_v2(
                                symbol=symbol.strip(),
                                start_date=start_date,
                                end_date=end_date,
                            )

                        # Store results for the dashboard.
                        st.session_state["asia_last_result"] = result

                        # ----------------------------------
                        # Recent successful runs
                        # ----------------------------------

                        recent_runs = st.session_state.setdefault(
                            "asia_recent_runs", []
                        )

                        recent_runs.insert(
                            0,
                            {
                                "run_id": result["run_id"],
                                "symbol": result["symbol"],
                                "start_date": result["start_date"],
                                "end_date": result["end_date"],
                                "candles": result["session"]["final_rows"],
                                "export_path": result["session"]["export"]["output_path"],
                            },
                        )

                        # Keep only the five latest successful runs.
                        del recent_runs[5:]

                    except Exception as exc:

                        st.error(
                            f"Asia Runner failed: {exc}"
                        )

                # ----------------------------------
                # Display successful execution
                # ----------------------------------

                last_result = st.session_state.get(
                    "asia_last_result"
                )

                if last_result is not None:

                    session_rows = last_result[
                        "session"
                    ]["final_rows"]

                    st.success(
                        "Asia Runner completed successfully! "
                        f"{session_rows:,} session candles exported."
                    )

                    # ----------------------------------
                    # Download exported Asia CSV
                    # ----------------------------------

                    export_info = last_result["session"]["export"]

                    try:
                        with open(export_info["output_path"], "rb") as csv_file:
                            csv_data = csv_file.read()

                    except OSError as exc:
                        st.error(
                            f"Could not prepare the CSV download: {exc}"
                        )

                    else:
                        st.download_button(
                            label="Download Asia CSV",
                            data=csv_data,
                            file_name=export_info["filename"],
                            mime="text/csv",
                            key="asia_download_csv",
                            use_container_width=True,
                        )

            # ----------------------------------
            # Other runners (coming soon)
            # ----------------------------------

            else:

                st.info(
                    "Runner parameters and execution controls "
                    "will be added in the next development stages."
                )

    # ------------------------------------------
    # Right-side runner information
    # ------------------------------------------

    with status_col:

        with st.container(border=True):

            st.subheader("Runner Status")

            if selected_page == "New York Runner":

                status_result = st.session_state.get(
                    "ny_last_result"
                )

                if status_result is not None:

                    st.success("Completed")

                    st.write(
                        f"**{status_result['session']['final_rows']:,} "
                        "session candles exported**"
                    )

                    st.caption(
                        f"Instrument: {status_result['symbol']}"
                    )

                else:

                    st.write("**Not started**")

                    st.caption(
                        "No successful execution recorded yet."
                    )

            elif selected_page == "London Runner":

                status_result = st.session_state.get(
                    "london_last_result"
                )

                if status_result is not None:

                    st.success("Completed")

                    st.write(
                        f"**{status_result['session']['final_rows']:,} "
                        "session candles exported**"
                    )

                    st.caption(
                        f"Instrument: {status_result['symbol']}"
                    )

                else:

                    st.write("**Not started**")

                    st.caption(
                        "No successful execution recorded yet."
                    )

            elif selected_page == "Asia Runner":

                status_result = st.session_state.get(
                    "asia_last_result"
                )

                if status_result is not None:

                    st.success("Completed")

                    st.write(
                        f"**{status_result['session']['final_rows']:,} "
                        "session candles exported**"
                    )

                    st.caption(
                        f"Instrument: {status_result['symbol']}"
                    )

                else:

                    st.write("**Not started**")

                    st.caption(
                        "No successful execution recorded yet."
                    )

            else:

                st.write("**Not started**")

                st.caption(
                    "No execution has started from this workspace."
                )

        # ------------------------------------------
        # Recent Runs panel
        # ------------------------------------------

        with st.container(border=True):

            st.subheader("Recent Runs")

            if selected_page == "New York Runner":

                recent_runs = st.session_state.get(
                    "ny_recent_runs", []
                )

                if recent_runs:

                    for index, run in enumerate(recent_runs):

                        st.write(
                            f"**{run['symbol']}**"
                        )

                        st.caption(
                            f"{run['start_date']} to "
                            f"{run['end_date']}"
                        )

                        st.caption(
                            f"{run['candles']:,} candles exported"
                        )

                        if index < len(recent_runs) - 1:
                            st.divider()

                else:

                    st.caption(
                        "No New York Runner executions recorded yet."
                    )

            elif selected_page == "London Runner":

                recent_runs = st.session_state.get(
                    "london_recent_runs", []
                )

                if recent_runs:

                    for index, run in enumerate(recent_runs):

                        st.write(
                            f"**{run['symbol']}**"
                        )

                        st.caption(
                            f"{run['start_date']} to "
                            f"{run['end_date']}"
                        )

                        st.caption(
                            f"{run['candles']:,} candles exported"
                        )

                        if index < len(recent_runs) - 1:
                            st.divider()

                else:

                    st.caption(
                        "No London Runner executions recorded yet."
                    )

            elif selected_page == "Asia Runner":

                recent_runs = st.session_state.get(
                    "asia_recent_runs", []
                )

                if recent_runs:

                    for index, run in enumerate(recent_runs):

                        st.write(
                            f"**{run['symbol']}**"
                        )

                        st.caption(
                            f"{run['start_date']} to "
                            f"{run['end_date']}"
                        )

                        st.caption(
                            f"{run['candles']:,} candles exported"
                        )

                        if index < len(recent_runs) - 1:
                            st.divider()

                else:

                    st.caption(
                        "No Asia Runner executions recorded yet."
                    )

            else:

                st.caption(
                    "No runs recorded for this runner yet."
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
