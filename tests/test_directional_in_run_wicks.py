"""Regression tests for directional in-run wick excursions."""

import unittest

import pandas as pd

from src.directional_runs import track_first_directional_run
from src.directional_multi_runs import detect_directional_runs


PRICES = [
    100, 101, 102, 103, 104,
    103.5, 104.5, 105,
    104, 103, 102, 101,
    100, 99, 98,
    99, 100, 101, 102, 103, 104, 105,
]


def make_candles(direction):
    closes = pd.Series(PRICES, dtype=float)

    data = pd.DataFrame({
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

    # Highest in-run wick occurs BEFORE structural endpoint.
    data.loc[6, "high"] = 108.0

    # An even higher wick occurs AFTER endpoint,
    # during reversal confirmation.
    data.loc[10, "high"] = 120.0

    if direction == "bearish":
        original = data[["open", "high", "low", "close"]].copy()

        data["open"] = 200 - original["open"]
        data["high"] = 200 - original["low"]
        data["low"] = 200 - original["high"]
        data["close"] = 200 - original["close"]

    return data


class TestDirectionalInRunWicks(unittest.TestCase):

    def check_direction(self, direction):
        candles = make_candles(direction)

        first = track_first_directional_run(
            candles,
            atr_period=3,
        )

        runs = detect_directional_runs(
            candles,
            atr_period=3,
        )

        self.assertIsNotNone(first)
        self.assertFalse(runs.empty)

        self.assertEqual(first["direction"], direction)
        self.assertEqual(first["start_index"], 0)
        self.assertEqual(first["end_index"], 7)

        # Structural close progress must remain unchanged.
        self.assertAlmostEqual(
            first["close_progress_points"], 5.0
        )

        # Existing endpoint and extended metrics.
        self.assertAlmostEqual(
            first["movement_points"], 5.5
        )
        self.assertAlmostEqual(
            first["maximum_wick_excursion_points"], 20.0
        )
        self.assertEqual(
            first["maximum_wick_excursion_index"], 10
        )

        # New metric: wick maximum THROUGH structural endpoint.
        self.assertAlmostEqual(
            first["maximum_in_run_wick_excursion_points"],
            8.0,
        )
        self.assertEqual(
            first["maximum_in_run_wick_excursion_index"],
            6,
        )

        # Single and multiple-run detectors must agree.
        for field in (
            "maximum_in_run_wick_excursion_points",
            "maximum_in_run_wick_excursion_index",
        ):
            self.assertEqual(
                runs.iloc[0][field],
                first[field],
            )

    def test_bullish_run(self):
        self.check_direction("bullish")

    def test_bearish_run(self):
        self.check_direction("bearish")


if __name__ == "__main__":
    unittest.main()
