
from __future__ import annotations

from datetime import date
from uuid import uuid4

from .config import RAW_DATA_DIR
from .mt5_fetcher import MT5FetchConfig, fetch_raw_candles
from .pipeline import (
    run_new_york_pipeline,
    run_london_pipeline,
)


# --------------------------------------------------
# Candle Fetcher 2.0
# New York Runner Integration
# --------------------------------------------------

def run_new_york_v2(
    symbol: str,
    start_date: date,
    end_date: date,
) -> dict:
    """
    Execute the complete New York Runner workflow.

    1. Validate configuration.
    2. Fetch raw M1 candles from MT5.
    3. Filter candles to the New York session.
    4. Export the session CSV.
    5. Return the results to the V2 dashboard.
    """

    # ------------------------------------------
    # Validate inputs
    # ------------------------------------------

    symbol = symbol.strip()

    if not symbol:
        raise ValueError("MT5 Instrument cannot be empty.")

    if start_date > end_date:
        raise ValueError(
            "Start Date must be on or before End Date."
        )

    start_text = start_date.isoformat()
    end_text = end_date.isoformat()

    # Unique identifier prevents overwriting
    # previous V2 exports.
    run_id = uuid4().hex[:12]

    # ------------------------------------------
    # Step 1 - Fetch raw MT5 candles
    # ------------------------------------------

    fetch_config = MT5FetchConfig(
        symbol=symbol,
        timeframe="M1",
        range_name="new_york",
        output_name=f"v2_ny_raw_{run_id}",
        start_date=start_text,
        end_date=end_text,
        output_folder=RAW_DATA_DIR,
        date_timezone_name="America/New_York",
    )

    raw_result = fetch_raw_candles(fetch_config)

    # ------------------------------------------
    # Step 2 - Process New York session
    # ------------------------------------------

    session_result = run_new_york_pipeline(
        symbol=symbol,
        timeframe="M1",
        start_date=start_text,
        end_date=end_text,
        raw_data_folder=RAW_DATA_DIR,
        input_pattern=raw_result["filename"],
        output_suffix=f"v2_{run_id}",
        save_output=True,
    )

    # ------------------------------------------
    # Step 3 - Return dashboard results
    # ------------------------------------------

    return {
        "run_id": run_id,
        "symbol": symbol,
        "timeframe": "M1",
        "start_date": start_text,
        "end_date": end_text,
        "raw": raw_result,
        "session": session_result,
        "status": "completed",
    }


# --------------------------------------------------
# Candle Fetcher 2.0
# London Runner Integration
# --------------------------------------------------

def run_london_v2(
    symbol: str,
    start_date: date,
    end_date: date,
) -> dict:
    """
    Execute the complete London Runner workflow.

    1. Validate configuration.
    2. Fetch raw M1 candles from MT5.
    3. Filter candles to the London session.
    4. Export the session CSV.
    5. Return the results to the V2 dashboard.
    """

    # ------------------------------------------
    # Validate inputs
    # ------------------------------------------

    symbol = symbol.strip()

    if not symbol:
        raise ValueError("MT5 Instrument cannot be empty.")

    if start_date > end_date:
        raise ValueError(
            "Start Date must be on or before End Date."
        )

    start_text = start_date.isoformat()
    end_text = end_date.isoformat()

    # Unique identifier prevents overwriting
    # previous V2 exports.
    run_id = uuid4().hex[:12]

    # ------------------------------------------
    # Step 1 - Fetch raw MT5 candles
    # ------------------------------------------

    fetch_config = MT5FetchConfig(
        symbol=symbol,
        timeframe="M1",
        range_name="london",
        output_name=f"v2_london_raw_{run_id}",
        start_date=start_text,
        end_date=end_text,
        output_folder=RAW_DATA_DIR,
        date_timezone_name="Europe/London",
    )

    raw_result = fetch_raw_candles(fetch_config)

    # ------------------------------------------
    # Step 2 - Process London session
    # ------------------------------------------

    session_result = run_london_pipeline(
        symbol=symbol,
        timeframe="M1",
        start_date=start_text,
        end_date=end_text,
        raw_data_folder=RAW_DATA_DIR,
        input_pattern=raw_result["filename"],
        output_suffix=f"v2_{run_id}",
        save_output=True,
    )

    # ------------------------------------------
    # Step 3 - Return dashboard results
    # ------------------------------------------

    return {
        "run_id": run_id,
        "symbol": symbol,
        "timeframe": "M1",
        "start_date": start_text,
        "end_date": end_text,
        "raw": raw_result,
        "session": session_result,
        "status": "completed",
    }
