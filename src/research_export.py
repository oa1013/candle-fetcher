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
        verify_historical_timeframe,
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

    timeframe_verification = None
    timeframe_decision = None

    h1_reference = None
    h1_candles = None
    h1_conflicting_rows = None

    h1_chunk_diagnostics = []

    h1_duplicate_diagnostics = {
        "identical_duplicates": 0,
        "conflicting_timestamps": 0,
    }

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
        # 4. Historical timeframe verification
        # ---------------------------------------------------

        stage = "timeframe_verification"

        reference_failure = None

        h1_reference = {
            "status": "not_requested",
            "rows_fetched": 0,
            "source_connection_matched": None,
        }

        if candles.empty:

            h1_reference["status"] = (
                "skipped_empty_m1_history"
            )

        else:

            try:

                reference = fetch_research_h1_reference(
                    fetched,
                    chunk_diagnostics=h1_chunk_diagnostics,
                    duplicate_diagnostics=(
                        h1_duplicate_diagnostics
                    ),
                )

                h1_candles = reference["candles"]

                h1_reference = {
                    key: reference[key]
                    for key in (
                        "provenance",
                        "requested_start_utc",
                        "requested_end_utc_exclusive",
                        "source_m1_end_utc_exclusive",
                        "chunk_days",
                        "timestamp_validation",
                        "rows_fetched",
                        "source_connection_matched",
                        "incomplete_hour_excluded",
                    )
                }

                h1_reference["status"] = (
                    "reference_available"
                    if not h1_candles.empty
                    else "no_reference_observations"
                )

            except Exception as error:

                reference_failure = (
                    "h1_reference_fetch_failed"
                )

                h1_reference["status"] = "failed"

                h1_reference["error_type"] = (
                    type(error).__name__
                )

                if isinstance(
                    error,
                    mt5_fetcher.CandleConflictError,
                ):

                    h1_conflicting_rows = (
                        error.conflicting_rows
                    )

        # Compare the validated M1 observations with H1.
        # If reference fetching failed, preserve the M1
        # observations and require review.

        comparison_reference = (
            h1_candles
            if h1_candles is not None
            else mt5_fetcher.empty_candle_dataframe()
        )

        try:

            timeframe_verification = (
                verify_historical_timeframe(
                    candles,
                    comparison_reference,
                )
            )

        except ValueError as error:

            if h1_candles is None:
                raise

            reference_failure = (
                "h1_reference_validation_failed"
            )

            h1_reference["status"] = (
                "reference_validation_failed"
            )

            h1_reference["error_type"] = (
                type(error).__name__
            )

            timeframe_verification = (
                verify_historical_timeframe(
                    candles,
                    mt5_fetcher.empty_candle_dataframe(),
                )
            )

        h1_reference["chunk_diagnostics"] = (
            sanitize_research_chunks(
                h1_chunk_diagnostics
            )
        )

        h1_reference["duplicate_diagnostics"] = (
            h1_duplicate_diagnostics
        )

        timeframe_decision = (
            evaluate_research_timeframe_export(
                timeframe_verification
            )
        )

        if reference_failure is not None:

            timeframe_decision["status"] = (
                "review_required"
            )

            timeframe_decision["allow_m1_export"] = (
                False
            )

            timeframe_decision[
                "blocking_reasons"
            ].append(reference_failure)

        warnings.extend(
            timeframe_verification["warnings"]
        )

        allow_m1_export = timeframe_decision[
            "allow_m1_export"
        ]

        if not allow_m1_export:

            warnings.append(
                "Observations preserved in quarantine. "
                "Publication as M1 history is not permitted."
            )

        # ---------------------------------------------------
        # 5. Export original observations to the appropriate
        #    destination without removing or changing rows
        # ---------------------------------------------------

        stage = "csv_export"

        if allow_m1_export:

            csv_folder = folder

            filename = f"US100.cash_M1_{year}.csv"

        else:

            csv_folder = folder / "quarantine"

            csv_folder.mkdir(exist_ok=False)

            filename = (
                f"US100.cash_M1_requested_{year}.csv"
            )

        csv_path = save_raw_research_csv(
            df=candles,
            output_folder=csv_folder,
            filename=filename,
        )

        # ---------------------------------------------------
        # 5. Construct research metadata
        # ---------------------------------------------------

        stage = "metadata_export"

        metadata = dict(fetched["provenance"])

        metadata["requested_timeframe"] = "M1"

        metadata["timeframe"] = (
            "M1"
            if allow_m1_export
            else "unverified"
        )

        metadata["timeframe_decision"] = (
            timeframe_decision
        )

        metadata["h1_reference"] = h1_reference

        metadata["native_m1_proven"] = False

        metadata["quarantined"] = (
            not allow_m1_export
        )

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
                else (
                    "observations_available"
                    if allow_m1_export
                    else "review_required"
                )
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

            "diagnostics_directory": (
                "diagnostics"
                if allow_m1_export
                else "../diagnostics"
            ),

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
            timeframe_verification=timeframe_verification,
            timeframe_decision=timeframe_decision,
            h1_reference=h1_reference,
            h1_candles=h1_candles,
            h1_conflicting_rows=h1_conflicting_rows,
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
                timeframe_verification=timeframe_verification,
                timeframe_decision=timeframe_decision,
                h1_reference=h1_reference,
                h1_candles=h1_candles,
                h1_conflicting_rows=h1_conflicting_rows,
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

        "m1_export_path": (
            csv_path
            if allow_m1_export
            else None
        ),

        "quarantine_path": (
            None
            if allow_m1_export
            else csv_path
        ),

        "timeframe_decision": timeframe_decision,

        "metadata_path": metadata_path,
        "diagnostics_path": (
            diagnostic_result["diagnostics_path"]
        ),
        "rows_exported": len(candles),
        "coverage_summary": coverage["summary"],
        "checksum_verified": True,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Historical timeframe export protection
# ---------------------------------------------------------------------------

def evaluate_research_timeframe_export(
    report: dict,
) -> dict:
    """
    Determine whether historical timeframe evidence
    supports publication as an M1 research dataset.

    This function makes a non-destructive decision.
    It does not modify, remove or export observations.
    """

    def require_mapping(mapping, key):

        value = mapping.get(key)

        if not isinstance(value, dict):
            raise ValueError(
                f"Missing or invalid report section: {key}"
            )

        return value

    def require_count(mapping, key):

        value = mapping.get(key)

        if (
            type(value) is not int
            or value < 0
        ):
            raise ValueError(
                f"Missing or invalid report count: {key}"
            )

        return value

    def require_boolean(mapping, key):

        value = mapping.get(key)

        if type(value) is not bool:
            raise ValueError(
                f"Missing or invalid report flag: {key}"
            )

        return value

    if not isinstance(report, dict):
        raise ValueError(
            "Timeframe verification report must be a dictionary."
        )

    # ---------------------------------------------------
    # 1. Validate the verification report
    # ---------------------------------------------------

    total = require_count(
        report, "total_observations"
    )

    reference_count = require_count(
        report, "reference_observations"
    )

    classification = report.get(
        "statistical_classification"
    )

    if not isinstance(classification, str):
        raise ValueError(
            "Missing statistical classification."
        )

    statistical = require_mapping(
        report, "statistical_validation"
    )

    direct = require_mapping(
        report, "direct_comparison"
    )

    aggregation = require_mapping(
        report, "aggregation_comparison"
    )

    has_minute_evidence = require_boolean(
        statistical,
        "has_minute_level_evidence",
    )

    suspected_rows = require_count(
        statistical,
        "suspected_hourly_rows",
    )

    regions = report.get(
        "suspected_hourly_regions"
    )

    if not isinstance(regions, list):
        raise ValueError(
            "Missing or invalid suspicious hourly regions."
        )

    verification_performed = require_boolean(
        report,
        "cross_timeframe_verification_performed",
    )

    direct_shared = require_count(
        direct, "shared_timestamps"
    )

    direct_matches = require_count(
        direct, "exact_matches"
    )

    complete_groups = require_count(
        aggregation, "complete_groups"
    )

    comparable_groups = require_count(
        aggregation, "comparable_groups"
    )

    aggregated_matches = require_count(
        aggregation, "exact_matches"
    )

    aggregation_mismatches = require_count(
        aggregation,
        "mismatched_shared_observations",
    )

    missing_references = require_count(
        aggregation,
        "observations_without_reference",
    )

    # Reject internally inconsistent counts.

    if (
        suspected_rows > total
        or direct_shared > min(total, reference_count)
        or direct_matches > direct_shared
        or complete_groups * 60 > total
        or comparable_groups > complete_groups
        or comparable_groups > direct_shared
        or aggregated_matches > comparable_groups
        or aggregated_matches + aggregation_mismatches
            != comparable_groups
        or comparable_groups + missing_references
            != complete_groups
    ):
        raise ValueError(
            "Inconsistent timeframe verification counts."
        )

    # ---------------------------------------------------
    # 2. Evaluate publication eligibility
    # ---------------------------------------------------

    blocking_reasons = []

    if total == 0:

        status = "no_observations"

        blocking_reasons.append(
            "no_observations"
        )

    else:

        if (
            suspected_rows > 0
            or regions
            or classification in (
                "suspected_hourly",
                "possible_mixed_timeframe",
            )
        ):
            blocking_reasons.append(
                "suspected_hourly_observations"
            )

        if (
            classification != "minute_level_evidence"
            or not has_minute_evidence
        ):
            blocking_reasons.append(
                "insufficient_minute_level_evidence"
            )

        if reference_count == 0:
            blocking_reasons.append(
                "missing_h1_reference"
            )

        if not verification_performed:
            blocking_reasons.append(
                "cross_timeframe_verification_missing"
            )

        if direct_matches > 0:
            blocking_reasons.append(
                "exact_direct_h1_matches"
            )

        if comparable_groups == 0:
            blocking_reasons.append(
                "no_comparable_hourly_groups"
            )

        if aggregation_mismatches > 0:
            blocking_reasons.append(
                "aggregation_mismatches"
            )

        if missing_references > 0:
            blocking_reasons.append(
                "missing_aggregation_reference"
            )

        status = (
            "review_required"
            if blocking_reasons
            else "minute_level_supported"
        )

    allow_export = (
        status == "minute_level_supported"
    )

    # ---------------------------------------------------
    # 3. Return a non-destructive export decision
    # ---------------------------------------------------

    return {
        "policy_version": 1,

        "status": status,

        "allow_m1_export": allow_export,

        "blocking_reasons": blocking_reasons,

        "statistical_classification": classification,

        "total_observations": total,

        "suspected_hourly_rows": suspected_rows,

        "reference_observations": reference_count,

        "direct_h1_matches": direct_matches,

        "complete_hourly_groups": complete_groups,

        "comparable_hourly_groups": comparable_groups,

        "matching_hourly_groups": aggregated_matches,

        "aggregation_mismatches": aggregation_mismatches,

        "missing_aggregation_references": (
            missing_references
        ),

        "preserve_original_observations": True,

        "automatic_row_removal_allowed": False,

        "native_m1_proven": False,

        "historical_completeness_verified": False,

        "limitation": (
            "Publication eligibility reflects the "
            "available statistical and cross-timeframe "
            "evidence. It does not prove the native "
            "timeframe of every observation or absolute "
            "historical market completeness."
        ),
    }


# ---------------------------------------------------------------------------
# Historical H1 reference extraction
# ---------------------------------------------------------------------------

def fetch_research_h1_reference(
    extraction: dict,
    *,
    chunk_diagnostics: list[dict] | None = None,
    duplicate_diagnostics: dict | None = None,
) -> dict:
    """
    Retrieve H1 reference observations for a historical
    M1 research extraction.

    Enforce matching broker, server, instrument,
    symbol specifications and timestamp convention.

    Exclude incomplete hourly reference candles.
    """

    import math

    from . import mt5_fetcher

    from .data_quality import (
        validate_ftmo_timestamp_consistency,
    )

    # ---------------------------------------------------
    # 1. Validate source extraction provenance
    # ---------------------------------------------------

    if not isinstance(extraction, dict):
        raise ValueError(
            "Invalid research extraction."
        )

    source = extraction.get("provenance")

    if not isinstance(source, dict):
        raise ValueError(
            "Missing source extraction provenance."
        )

    expected = {
        "symbol": "US100.cash",
        "timeframe": "M1",
        "server": mt5_fetcher.VERIFIED_FTMO_SERVER,
        "timestamp_mode": "ftmo_server",
    }

    for field, value in expected.items():

        if source.get(field) != value:

            raise ValueError(
                f"Incompatible source provenance: {field}"
            )

    broker = source.get("broker")

    if (
        not isinstance(broker, str)
        or not broker.strip()
    ):
        raise ValueError(
            "Missing source broker information."
        )

    digits = source.get("symbol_digits")
    point = source.get("symbol_point")

    if (
        type(digits) is not int
        or digits < 0
    ):
        raise ValueError(
            "Invalid source symbol digits."
        )

    if (
        type(point) not in (int, float)
        or not math.isfinite(point)
        or point <= 0
    ):
        raise ValueError(
            "Invalid source symbol point."
        )

    # ---------------------------------------------------
    # 2. Validate historical extraction boundaries
    # ---------------------------------------------------

    year = extraction.get("year")
    chunk_days = extraction.get("chunk_days")

    if (
        type(year) is not int
        or not 1 <= year <= 9998
    ):
        raise ValueError(
            "Invalid research calendar year."
        )

    if (
        type(chunk_days) is not int
        or chunk_days <= 0
    ):
        raise ValueError(
            "Invalid reference chunk size."
        )

    try:

        start_utc = datetime.fromisoformat(
            extraction["requested_start_utc"]
        )

        m1_end_utc = datetime.fromisoformat(
            extraction["requested_end_utc_exclusive"]
        )

    except (KeyError, TypeError, ValueError) as error:

        raise ValueError(
            "Invalid source extraction boundaries."
        ) from error

    if (
        start_utc.tzinfo is None
        or m1_end_utc.tzinfo is None
    ):
        raise ValueError(
            "Timezone-aware extraction boundaries required."
        )

    start_utc = start_utc.astimezone(UTC)
    m1_end_utc = m1_end_utc.astimezone(UTC)

    year_start = datetime(
        year, 1, 1, tzinfo=UTC
    )

    year_end = datetime(
        year + 1, 1, 1, tzinfo=UTC
    )

    if (
        start_utc != year_start
        or m1_end_utc < start_utc
        or m1_end_utc > year_end
    ):
        raise ValueError(
            "Invalid UTC calendar-year boundaries."
        )

    if (
        m1_end_utc.second != 0
        or m1_end_utc.microsecond != 0
    ):
        raise ValueError(
            "M1 cutoff must be minute-aligned."
        )

    # Only complete hours within the M1 extraction
    # period are eligible for reference comparison.

    end_utc_exclusive = m1_end_utc.replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    # ---------------------------------------------------
    # 3. Prepare independent H1 diagnostics
    # ---------------------------------------------------

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

    symbol = source["symbol"]

    # ---------------------------------------------------
    # 4. Connect and verify reference source
    # ---------------------------------------------------

    mt5_fetcher.initialize_mt5()

    try:

        account = mt5_fetcher.mt5.account_info()

        if account is None:
            raise ValueError(
                "Reference account information unavailable."
            )

        actual_broker = str(
            getattr(account, "company", "") or ""
        ).strip()

        actual_server = str(
            getattr(account, "server", "") or ""
        ).strip()

        if (
            actual_broker != broker
            or actual_server != source["server"]
        ):
            raise ValueError(
                "H1 reference connection provenance mismatch."
            )

        mt5_fetcher.ensure_symbol_available(symbol)

        symbol_info = mt5_fetcher.mt5.symbol_info(
            symbol
        )

        if symbol_info is None:
            raise ValueError(
                "Reference symbol information unavailable."
            )

        if (
            symbol_info.digits != digits
            or symbol_info.point != point
        ):
            raise ValueError(
                "H1 reference symbol specification mismatch."
            )

        provenance = {
            "symbol": symbol,
            "timeframe": "H1",
            "broker": actual_broker,
            "server": actual_server,
            "timestamp_mode": "ftmo_server",
            "symbol_digits": digits,
            "symbol_point": point,
            "calendar_timezone": "UTC",
            "session_filter": None,
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
        }

        # ------------------------------------------------
        # 5. Retrieve complete H1 reference observations
        # ------------------------------------------------

        if start_utc == end_utc_exclusive:

            candles = (
                mt5_fetcher.empty_candle_dataframe()
            )

        else:

            candles = mt5_fetcher.fetch_candles_by_range(
                symbol=symbol,
                timeframe_mt5=mt5_fetcher.mt5.TIMEFRAME_H1,
                start_utc=start_utc,
                end_utc_exclusive=end_utc_exclusive,
                chunk_days=chunk_days,
                ftmo_athens_clock=True,
                diagnostics=chunk_diagnostics,
                duplicate_diagnostics=duplicate_diagnostics,
            )

    finally:

        mt5_fetcher.shutdown_mt5()

    # ---------------------------------------------------
    # 6. Verify reference timestamp consistency
    # ---------------------------------------------------

    timestamp_validation = (
        validate_ftmo_timestamp_consistency(
            candles,
            start_utc=start_utc,
            end_utc_exclusive=end_utc_exclusive,
        )
    )

    if not timestamp_validation["is_consistent"]:
        raise ValueError(
            "H1 reference timestamp inconsistency."
        )

    if duplicate_diagnostics["conflicting_timestamps"]:
        raise ValueError(
            "Conflicting H1 reference observations."
        )

    # ---------------------------------------------------
    # 7. Return reference observations and provenance
    # ---------------------------------------------------

    return {
        "year": year,

        "candles": candles,

        "provenance": provenance,

        "requested_start_utc": (
            start_utc.isoformat()
        ),

        "requested_end_utc_exclusive": (
            end_utc_exclusive.isoformat()
        ),

        "source_m1_end_utc_exclusive": (
            m1_end_utc.isoformat()
        ),

        "chunk_days": chunk_days,

        "chunk_diagnostics": chunk_diagnostics,

        "duplicate_diagnostics": duplicate_diagnostics,

        "timestamp_validation": timestamp_validation,

        "rows_fetched": len(candles),

        "source_connection_matched": True,

        "incomplete_hour_excluded": True,
    }

