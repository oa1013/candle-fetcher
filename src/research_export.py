"""Dedicated native M1 historical research export engine."""

from __future__ import annotations

from datetime import datetime, timezone


UTC = timezone.utc


def get_research_year_bounds(
    year: int,
    as_of_utc: datetime,
) -> tuple[datetime, datetime]:
    """
    Return the UTC boundaries of a historical calendar year.

    The start boundary is inclusive.
    The end boundary is exclusive.

    For the current year, exclude the currently forming
    M1 candle by flooring the extraction time to a minute.
    """

    if (
        not isinstance(year, int)
        or isinstance(year, bool)
        or not 1 <= year <= 9998
    ):
        raise ValueError("Invalid calendar year.")

    if not isinstance(as_of_utc, datetime):
        raise ValueError("Extraction time must be a datetime.")

    if (
        as_of_utc.tzinfo is None
        or as_of_utc.utcoffset() is None
    ):
        raise ValueError(
            "Extraction time must be timezone-aware."
        )

    as_of_utc = as_of_utc.astimezone(UTC)

    if year > as_of_utc.year:
        raise ValueError(
            "Cannot extract a future calendar year."
        )

    start_utc = datetime(
        year, 1, 1, tzinfo=UTC
    )

    calendar_end_utc = datetime(
        year + 1, 1, 1, tzinfo=UTC
    )

    completed_candle_cutoff = as_of_utc.replace(
        second=0,
        microsecond=0,
    )

    end_utc_exclusive = min(
        calendar_end_utc,
        completed_candle_cutoff,
    )

    return start_utc, end_utc_exclusive


# ---------------------------------------------------------------------------
# Native FTMO M1 research extraction
# ---------------------------------------------------------------------------

def fetch_research_year(
    year: int,
    as_of_utc: datetime,
    chunk_days: int = 31,
    *,
    chunk_diagnostics: list[dict] | None = None,
    duplicate_diagnostics: dict | None = None,
) -> dict:
    """
    Fetch native US100.cash M1 observations for a UTC year.

    Research extraction is currently restricted to the
    verified FTMO-Server3 timestamp convention.

    No session filtering, interpolation, aggregation,
    resampling or artificial filling is performed.
    """

    from . import mt5_fetcher

    if (
        not isinstance(chunk_days, int)
        or isinstance(chunk_days, bool)
        or chunk_days <= 0
    ):
        raise ValueError(
            "chunk_days must be a positive integer."
        )

    start_utc, end_utc_exclusive = (
        get_research_year_bounds(
            year=year,
            as_of_utc=as_of_utc,
        )
    )

    symbol = "US100.cash"
    timeframe = "M1"

    if chunk_diagnostics is None:
        chunk_diagnostics = []

    if duplicate_diagnostics is None:
        duplicate_diagnostics = {}

    duplicate_diagnostics.setdefault(
        "identical_duplicates", 0
    )

    duplicate_diagnostics.setdefault(
        "conflicting_timestamps", 0
    )

    mt5_fetcher.initialize_mt5()

    try:
        account = mt5_fetcher.mt5.account_info()

        if account is None:
            raise RuntimeError(
                "No logged-in MT5 account was found."
            )

        server = str(
            getattr(account, "server", "") or ""
        ).strip()

        broker = str(
            getattr(account, "company", "") or ""
        ).strip()

        if server != mt5_fetcher.VERIFIED_FTMO_SERVER:
            raise RuntimeError(
                f"Unverified MT5 server: {server!r}. "
                "Research extraction currently requires "
                "FTMO-Server3."
            )

        if not broker:
            raise RuntimeError(
                "MT5 broker information is unavailable."
            )

        mt5_fetcher.ensure_symbol_available(symbol)

        symbol_info = mt5_fetcher.mt5.symbol_info(
            symbol
        )

        if symbol_info is None:
            raise RuntimeError(
                f"Symbol information unavailable: {symbol}"
            )

        provenance = {
            "symbol": symbol,
            "timeframe": timeframe,
            "broker": broker,
            "server": server,
            "timestamp_mode": "ftmo_server",
            "symbol_digits": int(symbol_info.digits),
            "symbol_point": float(symbol_info.point),
            "mt5_package_version": (
                str(mt5_fetcher.mt5.__version__)
                if isinstance(
                    getattr(
                        mt5_fetcher.mt5,
                        "__version__",
                        None,
                    ),
                    str,
                )
                else None
            ),
            "calendar_timezone": "UTC",
            "session_filter": None,
            "original_timestamp_column": "mt5_time_raw",
            "corrected_timestamp_column": "datetime",
            "timestamp_correction": (
                "FTMO server wall clock equals "
                "New York wall clock plus seven hours; "
                "converted to genuine UTC."
            ),
        }

        if start_utc == end_utc_exclusive:
            candles = (
                mt5_fetcher.empty_candle_dataframe()
            )

        else:
            candles = mt5_fetcher.fetch_candles_by_range(
                symbol=symbol,
                timeframe_mt5=mt5_fetcher.get_mt5_timeframe(
                    timeframe
                ),
                start_utc=start_utc,
                end_utc_exclusive=end_utc_exclusive,
                chunk_days=chunk_days,
                ftmo_athens_clock=True,
                diagnostics=chunk_diagnostics,
                duplicate_diagnostics=duplicate_diagnostics,
            )

    finally:
        mt5_fetcher.shutdown_mt5()

    return {
        "year": year,
        "candles": candles,
        "provenance": provenance,
        "requested_start_utc": start_utc.isoformat(),
        "requested_end_utc_exclusive": (
            end_utc_exclusive.isoformat()
        ),
        "as_of_utc": (
            as_of_utc.astimezone(UTC).isoformat()
        ),
        "chunk_days": chunk_days,
        "chunk_diagnostics": chunk_diagnostics,
        "duplicate_diagnostics": duplicate_diagnostics,
        "rows_fetched": len(candles),
    }


# ---------------------------------------------------------------------------
# Research provenance helpers
# ---------------------------------------------------------------------------

def get_research_git_provenance() -> dict:
    """Identify the source revision used for extraction."""

    import subprocess
    from pathlib import Path

    repository = Path(__file__).resolve().parents[1]

    result = {
        "git_commit": None,
        "git_working_tree_dirty": None,
    }

    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

        result["git_commit"] = revision.stdout.strip()

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

        result["git_working_tree_dirty"] = bool(
            status.stdout.strip()
        )

    except (OSError, subprocess.SubprocessError):
        pass

    return result


def sanitize_research_chunks(
    chunk_diagnostics: list[dict],
) -> list[dict]:
    """
    Preserve structured chunk diagnostics while withholding
    unrestricted broker error messages.

    Broker error messages can contain private information.
    """

    allowed_fields = (
        "requested_start_utc",
        "requested_end_utc_exclusive",
        "mt5_request_start",
        "mt5_request_end_inclusive",
        "status",
        "rows_returned",
        "first_datetime_utc",
        "last_datetime_utc",
        "retry_attempts",
    )

    sanitized = []

    for record in chunk_diagnostics:

        safe_record = {
            field: record[field]
            for field in allowed_fields
            if field in record
        }

        error = record.get("mt5_error")

        if error is None:
            safe_record["mt5_error"] = None

        else:

            error_code = None

            if (
                isinstance(error, (list, tuple))
                and len(error) > 0
                and isinstance(error[0], int)
            ):
                error_code = error[0]

            safe_record["mt5_error"] = [
                error_code,
                "Original MT5 error message withheld.",
            ]

        sanitized.append(safe_record)

    return sanitized


# ---------------------------------------------------------------------------
# Combined annual research extraction and export
# ---------------------------------------------------------------------------

def export_research_year(
    year: int,
    output_folder,
    as_of_utc: datetime | None = None,
    chunk_days: int = 31,
) -> dict:
    """
    Fetch, validate and export one UTC calendar year
    of native FTMO US100.cash M1 observations.

    Existing annual extraction directories are never
    overwritten.

    Invalid datasets are blocked from publication.
    Extraction failures retain diagnostic evidence.
    """

    from pathlib import Path

    from . import mt5_fetcher

    from .data_quality import (
        validate_raw_m1_candles,
        validate_ftmo_timestamp_consistency,
        build_research_coverage_report,
    )

    from .exports import (
        save_raw_research_csv,
        save_research_metadata,
        save_research_diagnostics,
        verify_research_checksum,
    )

    if as_of_utc is None:
        as_of_utc = datetime.now(UTC)

    start_utc, end_utc_exclusive = (
        get_research_year_bounds(
            year=year,
            as_of_utc=as_of_utc,
        )
    )

    if (
        not isinstance(chunk_days, int)
        or isinstance(chunk_days, bool)
        or chunk_days <= 0
    ):
        raise ValueError(
            "chunk_days must be a positive integer."
        )

    source_revision = get_research_git_provenance()

    folder = Path(output_folder) / str(year)

    # Reserve a new directory before connecting to MT5.
    # Previous extraction attempts must remain untouched.

    folder.mkdir(
        parents=True,
        exist_ok=False,
    )

    diagnostics_folder = folder / "diagnostics"

    chunk_diagnostics = []

    duplicate_diagnostics = {
        "identical_duplicates": 0,
        "conflicting_timestamps": 0,
    }

    coverage = None
    data_quality = None
    timestamp_validation = None

    csv_path = None
    metadata_path = None

    stage = "fetch"

    try:

        # ---------------------------------------------------
        # 1. Native historical extraction
        # ---------------------------------------------------

        fetched = fetch_research_year(
            year=year,
            as_of_utc=as_of_utc,
            chunk_days=chunk_days,
            chunk_diagnostics=chunk_diagnostics,
            duplicate_diagnostics=duplicate_diagnostics,
        )

        extracted_at_utc = datetime.now(UTC)

        candles = fetched["candles"]

        # ---------------------------------------------------
        # 2. Validate the raw observations
        # ---------------------------------------------------

        stage = "validation"

        data_quality = validate_raw_m1_candles(
            candles
        )

        timestamp_validation = (
            validate_ftmo_timestamp_consistency(
                candles,
                start_utc=start_utc,
                end_utc_exclusive=end_utc_exclusive,
            )
        )

        critical_fields = (
            "invalid_timestamp_rows",
            "non_minute_aligned_rows",
            "duplicate_timestamp_rows",
            "invalid_ohlc_rows",
            "invalid_ohlc_relationship_rows",
            "negative_volume_rows",
            "negative_spread_rows",
            "invalid_volume_rows",
            "invalid_spread_rows",
        )

        problems = [
            field
            for field in critical_fields
            if data_quality[field] > 0
        ]

        if not data_quality["is_chronologically_sorted"]:
            problems.append("incorrect_timestamp_order")

        if not timestamp_validation["is_consistent"]:
            problems.append("timestamp_inconsistency")

        if duplicate_diagnostics["conflicting_timestamps"]:
            problems.append("conflicting_timestamps")

        if problems:
            raise ValueError(
                "Research dataset validation failed: "
                + ", ".join(problems)
            )

        # ---------------------------------------------------
        # 3. Calculate historical coverage
        # ---------------------------------------------------

        stage = "coverage"

        coverage = build_research_coverage_report(
            candles,
            start_utc=start_utc,
            end_utc_exclusive=end_utc_exclusive,
        )

        warnings = []

        if candles.empty:
            warnings.append(
                "No historical observations returned."
            )

        if duplicate_diagnostics["identical_duplicates"]:
            warnings.append(
                "Identical duplicate observations were "
                "consolidated during fetching."
            )

        if any(
            record.get("status") == "empty"
            for record in chunk_diagnostics
        ):
            warnings.append(
                "One or more historical chunks returned "
                "zero observations."
            )

        warnings.append(
            "Historical market completeness is unverified."
        )

        if source_revision["git_commit"] is None:
            warnings.append(
                "Git source revision could not be identified."
            )

        if source_revision["git_working_tree_dirty"]:
            warnings.append(
                "Extraction used a modified Git working tree."
            )

        if fetched["provenance"]["mt5_package_version"] is None:
            warnings.append(
                "MT5 package version could not be identified."
            )

        safe_chunks = sanitize_research_chunks(
            chunk_diagnostics
        )

        # ---------------------------------------------------
        # 4. Export the original candle observations
        # ---------------------------------------------------

        stage = "csv_export"

        filename = f"US100.cash_M1_{year}.csv"

        csv_path = save_raw_research_csv(
            df=candles,
            output_folder=folder,
            filename=filename,
        )

        # ---------------------------------------------------
        # 5. Construct research metadata
        # ---------------------------------------------------

        stage = "metadata_export"

        metadata = dict(fetched["provenance"])

        metadata.update(source_revision)

        metadata.update({
            "year": year,

            "as_of_utc": fetched["as_of_utc"],

            "extracted_at_utc": (
                extracted_at_utc.isoformat()
            ),

            "requested_start_utc": (
                start_utc.isoformat()
            ),

            "requested_end_utc_exclusive": (
                end_utc_exclusive.isoformat()
            ),

            "first_datetime_utc": (
                coverage["summary"]["first_datetime_utc"]
            ),

            "last_datetime_utc": (
                coverage["summary"]["last_datetime_utc"]
            ),

            "rows_exported": len(candles),

            "data_status": (
                "no_observations"
                if candles.empty
                else "observations_available"
            ),

            "chunk_days": chunk_days,

            "chunk_diagnostics": safe_chunks,

            "duplicate_diagnostics": (
                duplicate_diagnostics
            ),

            "data_quality": data_quality,

            "timestamp_validation": (
                timestamp_validation
            ),

            "coverage_summary": coverage["summary"],

            "interpolation_applied": False,

            "resampling_applied": False,

            "aggregation_applied": False,

            "missing_candles_filled": False,

            "price_rounding_applied": False,

            "zero_volume_candles_removed": False,

            "currently_forming_candle_excluded": True,

            "historical_completeness_verified": False,

            "diagnostics_directory": "diagnostics",

            "warnings": warnings,
        })

        metadata_path = save_research_metadata(
            csv_path=csv_path,
            metadata=metadata,
        )

        stage = "checksum_verification"

        if not verify_research_checksum(csv_path):
            raise RuntimeError(
                "Research CSV checksum verification failed."
            )

        # ---------------------------------------------------
        # 6. Save permanent diagnostic reports
        # ---------------------------------------------------

        stage = "diagnostic_export"

        diagnostic_result = save_research_diagnostics(
            output_folder=diagnostics_folder,
            chunk_diagnostics=safe_chunks,
            duplicate_diagnostics=duplicate_diagnostics,
            coverage=coverage,
        )

    except Exception as error:

        # Remove unpublished outputs created by this attempt.
        # Keep the annual folder and diagnostic evidence.

        for created_path in (metadata_path, csv_path):

            if created_path is not None:
                try:
                    created_path.unlink(missing_ok=True)

                except OSError:
                    error.add_note(
                        "An incomplete export could not "
                        "be removed."
                    )

        conflicting_rows = None

        if isinstance(
            error,
            mt5_fetcher.CandleConflictError,
        ):
            conflicting_rows = error.conflicting_rows

        # Do not publish unrestricted exception messages,
        # tracebacks or account information.

        failure = {
            "error_type": type(error).__name__,
            "stage": stage,
            "message": (
                f"Research extraction failed during {stage}. "
                "Original exception message withheld."
            ),
            "year": year,
            "requested_start_utc": start_utc.isoformat(),
            "requested_end_utc_exclusive": (
                end_utc_exclusive.isoformat()
            ),
            "data_quality": data_quality,
            "timestamp_validation": timestamp_validation,
        }

        try:
            save_research_diagnostics(
                output_folder=diagnostics_folder,
                chunk_diagnostics=(
                    sanitize_research_chunks(
                        chunk_diagnostics
                    )
                ),
                duplicate_diagnostics=(
                    duplicate_diagnostics
                ),
                coverage=coverage,
                conflicting_rows=conflicting_rows,
                failure=failure,
            )

        except Exception as diagnostic_error:

            error.add_note(
                "Failure diagnostic export also failed: "
                + type(diagnostic_error).__name__
            )

        # Preserve the original exception type.
        raise

    return {
        "year": year,
        "output_folder": folder,
        "csv_path": csv_path,
        "metadata_path": metadata_path,
        "diagnostics_path": (
            diagnostic_result["diagnostics_path"]
        ),
        "rows_exported": len(candles),
        "coverage_summary": coverage["summary"],
        "checksum_verified": True,
        "warnings": warnings,
    }

