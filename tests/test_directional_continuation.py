"""
Candle Fetcher — Directional Continuation Tests.

Tests historical M1 candle validation, timezone handling,
gap detection, and Wilder ATR calculations.
"""

import unittest

import numpy as np
import pandas as pd

from src.directional_continuation import (
    prepare_m1_candles,
    calculate_wilder_atr,
)


def make_test_candles(count=20):
    """Create deterministic M1 candles for testing."""

    times = pd.date_range(
        "2025-07-15 13:00",
        periods=count,
        freq="min",
        tz="UTC",
    )

    prices = np.arange(count, dtype=float) + 100.0

    return pd.DataFrame({
        "datetime": times,
        "open": prices,
        "high": prices + 2.0,
        "low": prices - 1.0,
        "close": prices + 1.0,
    })


class TestDirectionalFoundation(unittest.TestCase):

    def test_valid_candles(self):
        candles = make_test_candles()

        result = prepare_m1_candles(candles)

        self.assertEqual(len(result), 20)
        self.assertEqual(result["segment_id"].nunique(), 1)

        self.assertTrue(
            result["datetime"].is_monotonic_increasing
        )

    def test_wilder_atr(self):
        candles = make_test_candles()

        result = calculate_wilder_atr(
            candles,
            period=14,
        )

        self.assertTrue(
            result["atr"].iloc[:13].isna().all()
        )

        self.assertAlmostEqual(
            result["atr"].iloc[13],
            3.0,
            places=10,
        )

        self.assertAlmostEqual(
            result["atr"].iloc[-1],
            3.0,
            places=10,
        )

    def test_gap_detection(self):
        candles = make_test_candles()

        extra = make_test_candles(3)

        extra["datetime"] = pd.date_range(
            "2025-07-15 14:00",
            periods=3,
            freq="min",
            tz="UTC",
        )

        combined = pd.concat(
            [candles, extra],
            ignore_index=True,
        )

        result = calculate_wilder_atr(combined)

        self.assertEqual(
            result["segment_id"].nunique(),
            2,
        )

        self.assertTrue(
            result["atr"].iloc[-3:].isna().all()
        )

    def test_duplicate_timestamps_rejected(self):
        candles = make_test_candles()

        candles.loc[5, "datetime"] = candles.loc[
            4, "datetime"
        ]

        with self.assertRaises(ValueError):
            prepare_m1_candles(candles)

    def test_naive_timestamps_rejected(self):
        candles = make_test_candles()

        candles["datetime"] = (
            candles["datetime"].dt.tz_localize(None)
        )

        with self.assertRaises(ValueError):
            prepare_m1_candles(candles)

    def test_unsorted_timestamps_rejected(self):
        candles = make_test_candles()

        candles = candles.iloc[::-1].reset_index(
            drop=True
        )

        with self.assertRaises(ValueError):
            prepare_m1_candles(candles)

    def test_invalid_ohlc_rejected(self):
        candles = make_test_candles()

        candles.loc[3, "high"] = (
            candles.loc[3, "low"] - 1.0
        )

        with self.assertRaises(ValueError):
            prepare_m1_candles(candles)

    def test_invalid_atr_period_rejected(self):
        candles = make_test_candles()

        with self.assertRaises(ValueError):
            calculate_wilder_atr(
                candles,
                period=0,
            )

    def test_missing_column_rejected(self):
        candles = make_test_candles()

        candles = candles.drop(columns=["high"])

        with self.assertRaises(ValueError):
            prepare_m1_candles(candles)

    def test_timezone_conversion(self):
        candles = make_test_candles()

        candles["datetime"] = (
            candles["datetime"]
            .dt.tz_convert("Europe/London")
        )

        result = prepare_m1_candles(candles)

        self.assertEqual(
            str(result["datetime"].dt.tz),
            "UTC",
        )

        self.assertEqual(
            result["datetime"].iloc[0],
            pd.Timestamp("2025-07-15 13:00:00+00:00"),
        )


if __name__ == "__main__":
    unittest.main()
