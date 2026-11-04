"""
Regression tests for start-candle wick inflation.

The movement begins at the starting candle's close.
An earlier wick must not be counted as forward movement.
"""

import unittest

import pandas as pd

from src.directional_runs import track_first_directional_run
from src.directional_multi_runs import detect_directional_runs


PRICES = [
    100, 101, 102, 103, 104,
    103.5, 104.5, 105,
    104, 103, 102, 101,
]


def make_candles(bearish=False):
    prices = (
        [300 - price for price in PRICES]
        if bearish else PRICES
    )

    closes = pd.Series(prices, dtype=float)

    return pd.DataFrame({
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


class TestStartCandleWicks(unittest.TestCase):

    def check_run(self, bearish, multiple):
        candles = make_candles(bearish=bearish)

        if bearish:
            candles.loc[0, "low"] = 180.0
            expected_end_price = 194.5
        else:
            candles.loc[0, "high"] = 120.0
            expected_end_price = 105.5

        settings = {
            "atr_period": 3,
            "min_atr_fraction": 0.1,
        }

        if multiple:
            results = detect_directional_runs(
                candles, **settings
            )
            self.assertFalse(results.empty)
            run = results.iloc[0].to_dict()
        else:
            run = track_first_directional_run(
                candles, **settings
            )
            self.assertIsNotNone(run)

        self.assertEqual(run["start_index"], 0)
        self.assertEqual(run["end_index"], 7)

        self.assertAlmostEqual(
            run["end_price"],
            expected_end_price,
        )
        self.assertAlmostEqual(
            run["movement_points"],
            5.5,
        )
        self.assertAlmostEqual(
            run["duration_minutes"],
            7.0,
        )

        # The wick should remain included in ATR.
        self.assertGreater(
            run["atr_at_start_confirmation"],
            4.0,
        )

    def test_bullish_single_run(self):
        self.check_run(bearish=False, multiple=False)

    def test_bearish_single_run(self):
        self.check_run(bearish=True, multiple=False)

    def test_bullish_multi_run(self):
        self.check_run(bearish=False, multiple=True)

    def test_bearish_multi_run(self):
        self.check_run(bearish=True, multiple=True)


if __name__ == "__main__":
    unittest.main()
