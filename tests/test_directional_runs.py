"""
Candle Fetcher — Method B Directional Run Tests.

Permanent synthetic tests for pullback-tolerant
historical movement tracking.
"""

import unittest

import pandas as pd

from src.directional_runs import track_first_directional_run


BASE_PRICES = [
    100, 101, 102, 103, 104,
    103.5, 104.5, 105,
    104, 103, 102, 101,
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


class TestDirectionalRuns(unittest.TestCase):

    def track(self, prices=None, **settings):
        if prices is None:
            prices = BASE_PRICES

        return track_first_directional_run(
            make_candles(prices),
            atr_period=3,
            **settings,
        )

    def test_bullish_run_and_reversal(self):
        result = self.track()

        self.assertEqual(result["direction"], "bullish")
        self.assertEqual(
            result["status"], "reversal_confirmed"
        )
        self.assertEqual(result["start_index"], 0)
        self.assertEqual(
            result["start_confirmation_index"], 2
        )
        self.assertEqual(result["end_index"], 7)
        self.assertEqual(
            result["reversal_confirmation_index"], 10
        )
        self.assertAlmostEqual(
            result["movement_points"], 5.5
        )
        self.assertEqual(result["duration_minutes"], 7.0)

    def test_bearish_run_and_reversal(self):
        prices = [300 - value for value in BASE_PRICES]

        result = self.track(prices)

        self.assertEqual(result["direction"], "bearish")
        self.assertEqual(
            result["status"], "reversal_confirmed"
        )
        self.assertEqual(result["end_index"], 7)
        self.assertEqual(
            result["reversal_confirmation_index"], 10
        )
        self.assertAlmostEqual(
            result["movement_points"], 5.5
        )

    def test_small_pullback_does_not_end_run(self):
        result = self.track(BASE_PRICES[:8])

        self.assertEqual(
            result["status"], "incomplete_end_of_data"
        )
        self.assertEqual(result["end_index"], 7)
        self.assertIsNone(
            result["reversal_confirmation_index"]
        )

    def test_one_opposing_close_is_not_enough(self):
        result = self.track([
            100, 101, 102, 103, 104, 100, 101
        ])

        self.assertEqual(
            result["status"], "incomplete_end_of_data"
        )
        self.assertIsNone(
            result["reversal_confirmation_index"]
        )

    def test_two_weak_opposing_closes_are_not_enough(self):
        result = self.track([
            100, 101, 102, 103, 104, 103.5, 103
        ])

        self.assertEqual(
            result["status"], "incomplete_end_of_data"
        )
        self.assertIsNone(
            result["reversal_confirmation_index"]
        )

    def test_reversal_fraction_delays_confirmation(self):
        normal = self.track()
        stricter = self.track(
            reversal_move_fraction=0.8
        )

        self.assertEqual(
            normal["reversal_confirmation_index"], 10
        )
        self.assertEqual(
            stricter["reversal_confirmation_index"], 11
        )

    def test_large_atr_multiple_prevents_reversal(self):
        result = self.track(
            reversal_atr_multiple=10.0
        )

        self.assertEqual(
            result["status"], "incomplete_end_of_data"
        )

    def test_opposite_close_setting_is_respected(self):
        prices = [
            100, 101, 102, 103, 104, 100, 99
        ]

        one_close = self.track(
            prices,
            min_opposite_closes=1,
        )

        two_closes = self.track(
            prices,
            min_opposite_closes=2,
        )

        self.assertEqual(
            one_close["reversal_confirmation_index"], 5
        )
        self.assertEqual(
            two_closes["reversal_confirmation_index"], 6
        )

    def test_gap_marks_run_as_incomplete(self):
        candles = make_candles(
            BASE_PRICES,
            gap_at=6,
        )

        result = track_first_directional_run(
            candles,
            atr_period=3,
        )

        self.assertEqual(
            result["status"], "incomplete_gap"
        )
        self.assertIsNone(
            result["reversal_confirmation_index"]
        )

    def test_no_start_returns_none(self):
        result = self.track([100] * 20)

        self.assertIsNone(result)

    def test_atr_warmup_returns_none(self):
        result = track_first_directional_run(
            make_candles([100, 101, 102, 103]),
            atr_period=14,
        )

        self.assertIsNone(result)

    def test_invalid_parameters_rejected(self):
        invalid_settings = [
            ("reversal_atr_multiple", 0),
            ("reversal_atr_multiple", -2),
            ("reversal_atr_multiple", True),
            ("reversal_atr_multiple", float("nan")),
            ("reversal_atr_multiple", float("inf")),
            ("reversal_move_fraction", -0.1),
            ("reversal_move_fraction", 1.1),
            ("reversal_move_fraction", True),
            ("reversal_move_fraction", float("nan")),
            ("reversal_move_fraction", float("inf")),
            ("min_opposite_closes", 0),
            ("min_opposite_closes", -1),
            ("min_opposite_closes", True),
            ("min_opposite_closes", 1.5),
        ]

        for name, value in invalid_settings:
            with self.subTest(name=name, value=value):
                with self.assertRaises(ValueError):
                    self.track(**{name: value})

    def test_original_dataframe_is_unchanged(self):
        candles = make_candles(BASE_PRICES)
        original = candles.copy(deep=True)

        track_first_directional_run(
            candles,
            atr_period=3,
        )

        pd.testing.assert_frame_equal(
            candles,
            original,
        )

    def test_future_candles_do_not_change_completed_run(self):
        result = self.track(
            BASE_PRICES + [120, 121, 122]
        )

        self.assertEqual(
            result["status"], "reversal_confirmed"
        )
        self.assertEqual(result["end_index"], 7)
        self.assertEqual(
            result["reversal_confirmation_index"], 10
        )

    def test_only_first_run_is_returned(self):
        result = self.track(
            BASE_PRICES + [102, 103, 104, 105]
        )

        self.assertEqual(result["direction"], "bullish")
        self.assertEqual(result["start_index"], 0)
        self.assertEqual(result["end_index"], 7)


if __name__ == "__main__":
    unittest.main()
