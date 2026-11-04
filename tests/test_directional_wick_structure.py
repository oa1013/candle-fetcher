"""
Candle Fetcher — Wick-Sensitive Structure Tests.

Regression tests to ensure an isolated wick does not
change close-confirmed directional movement boundaries.

These tests initially reproduce a known engine bug.
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
        [300 - price for price in BASE_PRICES]
        if bearish
        else BASE_PRICES
    )

    closes = pd.Series(prices, dtype=float)

    return pd.DataFrame({
        "datetime": pd.date_range(
            "2025-07-15 13:00",
            periods=len(prices),
            freq="min",
            tz="UTC",
        ),
        "open": closes - 0.2,
        "high": closes + 0.5,
        "low": closes - 0.5,
        "close": closes,
    })


def add_extreme_wick(candles, bearish=False):
    modified = candles.copy(deep=True)

    if bearish:
        modified.loc[10, "low"] = 180.0
    else:
        modified.loc[10, "high"] = 120.0

    return modified


class TestWickStructure(unittest.TestCase):

    def test_normal_movement_sequence(self):
        candles = make_candles()

        runs = detect_directional_runs(
            candles,
            atr_period=3,
        )

        self.assertEqual(
            runs["direction"].tolist(),
            ["bullish", "bearish", "bullish"],
        )

        self.assertEqual(
            runs["end_index"].tolist(),
            [7, 14, 21],
        )

    def test_bullish_single_run_wick(self):
        candles = add_extreme_wick(
            make_candles()
        )

        result = track_first_directional_run(
            candles,
            atr_period=3,
        )

        self.assertEqual(result["direction"], "bullish")
        self.assertEqual(result["end_index"], 7)
        self.assertEqual(
            result["reversal_confirmation_index"],
            10,
        )

    def test_bearish_single_run_wick(self):
        candles = add_extreme_wick(
            make_candles(bearish=True),
            bearish=True,
        )

        result = track_first_directional_run(
            candles,
            atr_period=3,
        )

        self.assertEqual(result["direction"], "bearish")
        self.assertEqual(result["end_index"], 7)
        self.assertEqual(
            result["reversal_confirmation_index"],
            10,
        )

    def test_bullish_multi_run_wick(self):
        candles = add_extreme_wick(
            make_candles()
        )

        runs = detect_directional_runs(
            candles,
            atr_period=3,
        )

        self.assertEqual(
            runs["direction"].tolist(),
            ["bullish", "bearish", "bullish"],
        )

        self.assertEqual(
            runs["end_index"].tolist(),
            [7, 14, 21],
        )

    def test_bearish_multi_run_wick(self):
        candles = add_extreme_wick(
            make_candles(bearish=True),
            bearish=True,
        )

        runs = detect_directional_runs(
            candles,
            atr_period=3,
        )

        self.assertEqual(
            runs["direction"].tolist(),
            ["bearish", "bullish", "bearish"],
        )

        self.assertEqual(
            runs["end_index"].tolist(),
            [7, 14, 21],
        )


if __name__ == "__main__":
    unittest.main()
