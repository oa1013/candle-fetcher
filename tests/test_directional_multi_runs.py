"""
Candle Fetcher — Multiple Directional Runs Tests.

Synthetic regression tests for Method B
multi-run detection and event boundaries.
"""

import unittest

import pandas as pd

from src.directional_multi_runs import (
    RUN_COLUMNS,
    detect_directional_runs,
)
from src.directional_runs import (
    track_first_directional_run,
)


BASE_PRICES = [
    100, 101, 102, 103, 104,
    103.5, 104.5, 105,
    104, 103, 102, 101,
    100, 99, 98,
    99, 100, 101, 102, 103, 104, 105,
]


def make_candles(prices, gap_at=None):
    closes = pd.Series(prices, dtype=float)

    candles = pd.DataFrame({
        "datetime": pd.date_range(
            "2025-07-15 13:00",
            periods=len(closes),
            freq="min",
            tz="UTC",
        ),
        "open": closes - 0.2,
        "high": closes + 0.5,
        "low": closes - 0.5,
        "close": closes,
    })

    if gap_at is not None:
        candles.loc[
            gap_at:, "datetime"
        ] += pd.Timedelta(minutes=10)

    return candles


class TestDirectionalMultiRuns(unittest.TestCase):

    def detect(self, prices=None, **settings):
        if prices is None:
            prices = BASE_PRICES

        return detect_directional_runs(
            make_candles(prices),
            atr_period=3,
            **settings,
        )

    def test_three_successive_runs(self):
        runs = self.detect()

        self.assertEqual(len(runs), 3)

        self.assertEqual(
            runs["direction"].tolist(),
            ["bullish", "bearish", "bullish"],
        )

        self.assertEqual(
            runs["status"].tolist(),
            [
                "reversal_confirmed",
                "reversal_confirmed",
                "incomplete_end_of_data",
            ],
        )

    def test_run_boundaries(self):
        runs = self.detect()

        self.assertEqual(
            runs["start_index"].tolist(),
            [0, 7, 14],
        )

        self.assertEqual(
            runs["end_index"].tolist(),
            [7, 14, 21],
        )

        self.assertTrue(
            runs["start_index"].is_monotonic_increasing
        )

        self.assertTrue(
            runs["end_index"].is_monotonic_increasing
        )

        self.assertEqual(
            runs["start_index"].nunique(),
            len(runs),
        )

    def test_reversal_confirmation_indices(self):
        runs = self.detect()

        self.assertEqual(
            runs["reversal_confirmation_index"]
            .iloc[:2]
            .astype(int)
            .tolist(),
            [10, 17],
        )

        self.assertTrue(
            pd.isna(
                runs.iloc[-1][
                    "reversal_confirmation_index"
                ]
            )
        )

    def test_movement_points(self):
        runs = self.detect()

        self.assertEqual(
            runs["movement_points"].tolist(),
            [5.5, 7.5, 7.5],
        )

        self.assertEqual(
            runs["duration_minutes"].tolist(),
            [7.0, 7.0, 7.0],
        )

    def test_first_run_matches_single_tracker(self):
        candles = make_candles(BASE_PRICES)

        first = track_first_directional_run(
            candles,
            atr_period=3,
        )

        multiple = detect_directional_runs(
            candles,
            atr_period=3,
        )

        for column in [
            "direction",
            "status",
            "start_index",
            "start_price",
            "start_confirmation_index",
            "end_index",
            "end_price",
            "movement_points",
            "duration_minutes",
            "reversal_confirmation_index",
        ]:
            with self.subTest(column=column):
                self.assertEqual(
                    multiple.iloc[0][column],
                    first[column],
                )

    def test_completed_and_incomplete_separated(self):
        runs = self.detect()

        completed = runs.loc[
            runs["status"] == "reversal_confirmed"
        ]

        incomplete = runs.loc[
            runs["status"] != "reversal_confirmed"
        ]

        self.assertEqual(len(completed), 2)
        self.assertEqual(len(incomplete), 1)

        self.assertAlmostEqual(
            completed["movement_points"].sum(),
            13.0,
        )

    def test_gap_creates_separate_segments(self):
        prices = [
            100, 101, 102, 103, 104, 105,
            110, 109, 108, 107, 106, 105, 104,
        ]

        candles = make_candles(
            prices,
            gap_at=6,
        )

        runs = detect_directional_runs(
            candles,
            atr_period=3,
        )

        self.assertEqual(
            runs["direction"].tolist(),
            ["bullish", "bearish"],
        )

        self.assertEqual(
            runs["status"].tolist(),
            [
                "incomplete_gap",
                "incomplete_end_of_data",
            ],
        )

        self.assertEqual(
            runs["segment_id"].tolist(),
            [1, 2],
        )

    def test_later_segment_without_earlier_start(self):
        prices = (
            [100] * 6
            + [110, 111, 112, 113, 114]
        )

        candles = make_candles(
            prices,
            gap_at=6,
        )

        runs = detect_directional_runs(
            candles,
            atr_period=3,
        )

        self.assertEqual(len(runs), 1)
        self.assertEqual(
            runs.iloc[0]["segment_id"],
            2,
        )
        self.assertEqual(
            runs.iloc[0]["direction"],
            "bullish",
        )

    def test_no_reversal_is_one_incomplete_run(self):
        runs = self.detect([
            100, 101, 102, 103, 104,
            103.5, 104.5, 105, 106,
        ])

        self.assertEqual(len(runs), 1)

        self.assertEqual(
            runs.iloc[0]["status"],
            "incomplete_end_of_data",
        )

    def test_strict_reversal_threshold(self):
        runs = self.detect(
            reversal_atr_multiple=10.0,
        )

        self.assertEqual(len(runs), 1)

        self.assertEqual(
            runs.iloc[0]["status"],
            "incomplete_end_of_data",
        )

    def test_flat_data_returns_empty_table(self):
        runs = self.detect([100] * 20)

        self.assertTrue(runs.empty)

        self.assertEqual(
            runs.columns.tolist(),
            RUN_COLUMNS,
        )

    def test_atr_warmup_returns_empty_table(self):
        candles = make_candles([
            100, 101, 102, 103,
        ])

        runs = detect_directional_runs(
            candles,
            atr_period=14,
        )

        self.assertTrue(runs.empty)

    def test_invalid_settings_rejected(self):
        invalid_settings = [
            ("reversal_atr_multiple", 0),
            ("reversal_atr_multiple", -1),
            ("reversal_atr_multiple", True),
            ("reversal_atr_multiple", float("nan")),
            ("reversal_atr_multiple", float("inf")),
            ("reversal_move_fraction", -0.1),
            ("reversal_move_fraction", 1.1),
            ("reversal_move_fraction", True),
            ("reversal_move_fraction", float("nan")),
            ("min_opposite_closes", 0),
            ("min_opposite_closes", -1),
            ("min_opposite_closes", True),
            ("min_opposite_closes", 1.5),
        ]

        for name, value in invalid_settings:
            with self.subTest(name=name, value=value):
                with self.assertRaises(ValueError):
                    self.detect(**{name: value})

    def test_original_dataframe_unchanged(self):
        candles = make_candles(BASE_PRICES)
        original = candles.copy(deep=True)

        detect_directional_runs(
            candles,
            atr_period=3,
        )

        pd.testing.assert_frame_equal(
            candles,
            original,
        )

    def test_future_data_preserves_first_run(self):
        original = self.detect()

        extended = self.detect(
            BASE_PRICES + [
                106, 107, 108, 109,
            ]
        )

        self.assertEqual(
            original.iloc[0]["start_index"],
            extended.iloc[0]["start_index"],
        )

        self.assertEqual(
            original.iloc[0]["end_index"],
            extended.iloc[0]["end_index"],
        )

        self.assertEqual(
            original.iloc[0]["reversal_confirmation_index"],
            extended.iloc[0]["reversal_confirmation_index"],
        )


if __name__ == "__main__":
    unittest.main()
