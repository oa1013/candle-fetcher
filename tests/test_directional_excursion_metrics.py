"""
Candle Fetcher — Directional Excursion Metrics Tests.

Verifies that structural progress, endpoint-candle
movement, and maximum wick excursion remain distinct.
"""

import unittest

import pandas as pd

from src.directional_runs import track_first_directional_run
from src.directional_multi_runs import detect_directional_runs


BASE_PRICES = [
    100, 101, 102, 103, 104,
    103.5, 104.5, 105,
    104, 103, 102, 101,
    100, 99, 98,
    99, 100, 101, 102, 103, 104, 105,
]


def make_candles(bearish=False):
    prices = (
        [300 - value for value in BASE_PRICES]
        if bearish else BASE_PRICES
    )

    close = pd.Series(prices, dtype=float)

    return pd.DataFrame({
        "datetime": pd.date_range(
            "2025-07-15 13:00",
            periods=len(prices),
            freq="min",
            tz="UTC",
        ),
        "open": close - 0.2,
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
    })


def add_reversal_wick(candles, bearish=False):
    result = candles.copy(deep=True)

    if bearish:
        result.loc[10, "low"] = 180.0
    else:
        result.loc[10, "high"] = 120.0

    return result


class TestDirectionalExcursionMetrics(unittest.TestCase):

    def test_bullish_metric_separation(self):
        candles = add_reversal_wick(
            make_candles()
        )

        result = track_first_directional_run(
            candles,
            atr_period=3,
        )

        self.assertEqual(result["end_index"], 7)
        self.assertEqual(
            result["reversal_confirmation_index"], 10
        )

        self.assertAlmostEqual(
            result["close_progress_points"], 5.0
        )
        self.assertAlmostEqual(
            result["movement_points"], 5.5
        )
        self.assertAlmostEqual(
            result["maximum_wick_excursion_points"], 20.0
        )
        self.assertEqual(
            result["maximum_wick_excursion_index"], 10
        )

    def test_bearish_metric_separation(self):
        candles = add_reversal_wick(
            make_candles(bearish=True),
            bearish=True,
        )

        result = track_first_directional_run(
            candles,
            atr_period=3,
        )

        self.assertEqual(result["end_index"], 7)

        self.assertAlmostEqual(
            result["close_progress_points"], 5.0
        )
        self.assertAlmostEqual(
            result["movement_points"], 5.5
        )
        self.assertAlmostEqual(
            result["maximum_wick_excursion_points"], 20.0
        )
        self.assertEqual(
            result["maximum_wick_excursion_index"], 10
        )

    def test_single_and_multiple_trackers_agree(self):
        for bearish in [False, True]:
            with self.subTest(bearish=bearish):
                candles = add_reversal_wick(
                    make_candles(bearish),
                    bearish,
                )

                single = track_first_directional_run(
                    candles,
                    atr_period=3,
                )

                multiple = detect_directional_runs(
                    candles,
                    atr_period=3,
                ).iloc[0]

                for field in [
                    "end_index",
                    "movement_points",
                    "close_progress_points",
                    "maximum_wick_excursion_points",
                    "maximum_wick_excursion_index",
                ]:
                    self.assertEqual(
                        single[field],
                        multiple[field],
                    )

    def test_wick_after_confirmation_is_excluded(self):
        candles = add_reversal_wick(
            make_candles()
        )

        # The first run is confirmed at candle 10.
        # A later wick cannot change its statistics.
        candles.loc[11, "high"] = 150.0

        result = track_first_directional_run(
            candles,
            atr_period=3,
        )

        self.assertEqual(
            result["reversal_confirmation_index"], 10
        )
        self.assertEqual(
            result["maximum_wick_excursion_index"], 10
        )
        self.assertAlmostEqual(
            result["maximum_wick_excursion_points"], 20.0
        )

    def test_reference_candle_wick_excluded(self):
        candles = make_candles()
        candles.loc[0, "high"] = 120.0

        result = track_first_directional_run(
            candles,
            atr_period=3,
            min_atr_fraction=0.1,
        )

        self.assertEqual(result["start_index"], 0)
        self.assertEqual(result["end_index"], 7)

        self.assertAlmostEqual(
            result["close_progress_points"], 5.0
        )
        self.assertAlmostEqual(
            result["maximum_wick_excursion_points"], 5.5
        )


if __name__ == "__main__":
    unittest.main()
