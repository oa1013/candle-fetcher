import copy

import pytest

from src import research_export


def make_report():

    return {
        "total_observations": 180,

        "reference_observations": 3,

        "statistical_classification": (
            "minute_level_evidence"
        ),

        "statistical_validation": {
            "has_minute_level_evidence": True,
            "suspected_hourly_rows": 0,
        },

        "suspected_hourly_regions": [],

        "direct_comparison": {
            "shared_timestamps": 3,
            "exact_matches": 0,
        },

        "aggregation_comparison": {
            "complete_groups": 3,
            "comparable_groups": 3,
            "exact_matches": 3,
            "mismatched_shared_observations": 0,
            "observations_without_reference": 0,
        },

        "cross_timeframe_verification_performed": True,

        "native_m1_proven": False,

        "historical_completeness_verified": False,
    }


def evaluate(report):

    return (
        research_export
        .evaluate_research_timeframe_export(report)
    )


def test_minute_level_export_allowed():

    result = evaluate(make_report())

    assert result["allow_m1_export"] is True

    assert result["status"] == (
        "minute_level_supported"
    )

    assert result["blocking_reasons"] == []

    assert result["native_m1_proven"] is False

    assert result[
        "historical_completeness_verified"
    ] is False


@pytest.mark.parametrize(
    "classification",
    [
        "suspected_hourly",
        "possible_mixed_timeframe",
    ],
)
def test_suspicious_timeframe_blocks_export(
    classification,
):

    report = make_report()

    report["statistical_classification"] = (
        classification
    )

    report["statistical_validation"][
        "suspected_hourly_rows"
    ] = 24

    report["suspected_hourly_regions"] = [{
        "first_row_position": 0,
        "last_row_position": 23,
        "observation_count": 24,
    }]

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert result["status"] == "review_required"

    assert "suspected_hourly_observations" in (
        result["blocking_reasons"]
    )


def test_direct_h1_matches_block_export():

    report = make_report()

    report["direct_comparison"][
        "exact_matches"
    ] = 1

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert "exact_direct_h1_matches" in (
        result["blocking_reasons"]
    )


def test_aggregation_mismatch_blocks_export():

    report = make_report()

    report["aggregation_comparison"][
        "exact_matches"
    ] = 2

    report["aggregation_comparison"][
        "mismatched_shared_observations"
    ] = 1

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert "aggregation_mismatches" in (
        result["blocking_reasons"]
    )


def test_missing_hourly_reference_blocks_export():

    report = make_report()

    report["reference_observations"] = 0

    report[
        "cross_timeframe_verification_performed"
    ] = False

    report["direct_comparison"][
        "shared_timestamps"
    ] = 0

    report["aggregation_comparison"].update({
        "comparable_groups": 0,
        "exact_matches": 0,
        "observations_without_reference": 3,
    })

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert "missing_h1_reference" in (
        result["blocking_reasons"]
    )


def test_missing_complete_group_reference():

    report = make_report()

    report["reference_observations"] = 2

    report["direct_comparison"][
        "shared_timestamps"
    ] = 2

    report["aggregation_comparison"].update({
        "comparable_groups": 2,
        "exact_matches": 2,
        "observations_without_reference": 1,
    })

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert "missing_aggregation_reference" in (
        result["blocking_reasons"]
    )


def test_no_comparable_hourly_groups():

    report = make_report()

    report["aggregation_comparison"].update({
        "complete_groups": 0,
        "comparable_groups": 0,
        "exact_matches": 0,
    })

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert "no_comparable_hourly_groups" in (
        result["blocking_reasons"]
    )


def test_insufficient_statistical_evidence():

    report = make_report()

    report["statistical_classification"] = (
        "insufficient_evidence"
    )

    report["statistical_validation"][
        "has_minute_level_evidence"
    ] = False

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert "insufficient_minute_level_evidence" in (
        result["blocking_reasons"]
    )


def test_verification_not_performed():

    report = make_report()

    report[
        "cross_timeframe_verification_performed"
    ] = False

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert "cross_timeframe_verification_missing" in (
        result["blocking_reasons"]
    )


def test_empty_dataset():

    report = make_report()

    report["total_observations"] = 0

    report["statistical_classification"] = (
        "no_observations"
    )

    report["statistical_validation"][
        "has_minute_level_evidence"
    ] = False

    report["direct_comparison"][
        "shared_timestamps"
    ] = 0

    report["aggregation_comparison"].update({
        "complete_groups": 0,
        "comparable_groups": 0,
        "exact_matches": 0,
    })

    report[
        "cross_timeframe_verification_performed"
    ] = False

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert result["status"] == "no_observations"


def test_multiple_blocking_reasons_preserved():

    report = make_report()

    report["direct_comparison"][
        "exact_matches"
    ] = 1

    report["aggregation_comparison"][
        "mismatched_shared_observations"
    ] = 1

    report["aggregation_comparison"][
        "exact_matches"
    ] = 2

    result = evaluate(report)

    assert result["allow_m1_export"] is False

    assert "exact_direct_h1_matches" in (
        result["blocking_reasons"]
    )

    assert "aggregation_mismatches" in (
        result["blocking_reasons"]
    )


def test_original_report_not_modified():

    report = make_report()

    original = copy.deepcopy(report)

    evaluate(report)

    assert report == original


def test_unknown_classification_blocks_export():

    report = make_report()

    report["statistical_classification"] = (
        "unknown"
    )

    result = evaluate(report)

    assert result["allow_m1_export"] is False


def test_incomplete_report_rejected():

    with pytest.raises(ValueError):

        evaluate({})
