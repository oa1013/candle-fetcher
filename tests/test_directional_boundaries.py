"""Tests for session-aware directional run classification."""

import unittest

import pandas as pd

from src.directional_continuation import prepare_m1_candles
from src.directional_boundaries import classify_incomplete_runs


def make_candles(times):
    times = pd.DatetimeIndex(times).tz_convert("UTC")

    return pd.DataFrame({
        "datetime": times,
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
    })


def session(day, last_time="12:29"):
    start = pd.Timestamp(
        f"{day} 09:10",
        tz="America/New_York",
    )

    end = pd.Timestamp(
        f"{day} {last_time}",
        tz="America/New_York",
    )

    return pd.date_range(
        start=start,
        end=end,
        freq="min",
    )


def classify(candles, runs):
    return classify_incomplete_runs(
        candles,
        runs,
        session_timezone="America/New_York",
        session_start="09:10",
        session_end="12:30",
    )


class TestDirectionalBoundaries(unittest.TestCase):

    def test_session_end_and_internal_missing_candle(self):
        day_one = session("2024-01-08")
        day_two = session("2024-01-09")

        day_two = day_two[
            day_two != pd.Timestamp(
                "2024-01-09 11:19",
                tz="America/New_York",
            )
        ]

        candles = make_candles(
            day_one.append(day_two)
        )

        prepared = prepare_m1_candles(candles)

        segment_ids = (
            prepared["segment_id"]
            .drop_duplicates()
            .tolist()
        )

        self.assertEqual(len(segment_ids), 3)

        runs = pd.DataFrame([
            {
                "segment_id": segment_ids[0],
                "status": "incomplete_gap",
            },
            {
                "segment_id": segment_ids[1],
                "status": "incomplete_gap",
            },
            {
                "segment_id": segment_ids[2],
                "status": "incomplete_end_of_data",
            },
        ])

        result = classify(candles, runs)

        self.assertEqual(
            result["incomplete_reason"].tolist(),
            [
                "session_window_end",
                "missing_historical_data",
                "session_window_end",
            ],
        )

    def test_dataset_ending_mid_session(self):
        candles = make_candles(
            session("2024-01-08", "11:45")
        )

        prepared = prepare_m1_candles(candles)

        runs = pd.DataFrame([{
            "segment_id": int(
                prepared["segment_id"].iloc[0]
            ),
            "status": "incomplete_end_of_data",
        }])

        result = classify(candles, runs)

        self.assertEqual(
            result.iloc[0]["incomplete_reason"],
            "dataset_end",
        )

    def test_early_overnight_gap_is_not_assumed_normal(self):
        day_one = session("2024-01-08", "11:45")
        day_two = session("2024-01-09")

        candles = make_candles(
            day_one.append(day_two)
        )

        prepared = prepare_m1_candles(candles)

        first_segment = int(
            prepared["segment_id"].iloc[0]
        )

        runs = pd.DataFrame([{
            "segment_id": first_segment,
            "status": "incomplete_gap",
        }])

        result = classify(candles, runs)

        self.assertEqual(
            result.iloc[0]["incomplete_reason"],
            "unclassified_boundary",
        )

    def test_completed_runs_preserved_and_input_unchanged(self):
        candles = make_candles(
            session("2024-01-08")
        )

        prepared = prepare_m1_candles(candles)

        runs = pd.DataFrame([
            {
                "segment_id": int(
                    prepared["segment_id"].iloc[0]
                ),
                "status": "reversal_confirmed",
            },
            {
                "segment_id": int(
                    prepared["segment_id"].iloc[0]
                ),
                "status": "incomplete_end_of_data",
            },
        ])

        original = runs.copy(deep=True)

        result = classify(candles, runs)

        self.assertTrue(
            pd.isna(
                result.iloc[0]["incomplete_reason"]
            )
        )

        self.assertEqual(
            result.iloc[1]["incomplete_reason"],
            "session_window_end",
        )

        pd.testing.assert_frame_equal(
            runs,
            original,
        )

        self.assertEqual(
            result["status"].tolist(),
            runs["status"].tolist(),
        )


if __name__ == "__main__":
    unittest.main()
