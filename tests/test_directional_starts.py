"""
Candle Fetcher — Directional Start Detector Tests.

Permanent synthetic tests for historical movement
start identification.
"""

import unittest

import pandas as pd

from src.directional_starts import (
    START_COLUMNS,
    detect_directional_starts,
)


def make_candles(prices, gap_after=None):
    """Construct deterministic, timezone-aware M1 candles."""

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

    if gap_after is not None:
        candles.loc[
            gap_after + 1:, "datetime"
        ] += pd.Timedelta(minutes=10)

    return candles


class TestDirectionalStarts(unittest.TestCase):

    def detect(self, prices, **kwargs):
        return detect_directional_starts(
            make_candles(prices),
            atr_period=3,
            **kwargs,
        )

    def test_bullish_and_bearish_starts(self):
        events = self.detect([
            100, 101, 102, 103, 104, 105,
            104, 103, 102, 101,
        ])

        self.assertEqual(
            events["direction"].tolist(),
            ["bullish", "bearish"],
        )

        self.assertEqual(
            events["start_index"].tolist(),
            [0, 5],
        )

        self.assertEqual(
            events["confirmation_index"].tolist(),
            [2, 7],
        )

        self.assertEqual(
            events["movement_points"].tolist(),
            [2.0, 2.0],
        )

    def test_one_event_per_directional_streak(self):
        events = self.detect([
            100, 101, 102, 103,
            104, 105, 106, 107,
        ])

        self.assertEqual(len(events), 1)
        self.assertEqual(
            events.iloc[0]["direction"],
            "bullish",
        )

    def test_flat_candle_resets_streak(self):
        events = self.detect([
            100, 101, 101, 102,
            103, 103, 104, 105,
        ])

        self.assertEqual(len(events), 2)

        self.assertEqual(
            events["start_index"].tolist(),
            [2, 5],
        )

        self.assertEqual(
            events["confirmation_index"].tolist(),
            [4, 7],
        )

    def test_direction_change_resets_streak(self):
        events = self.detect([
            100, 101, 102,
            101, 100, 99,
            100, 101, 102,
        ])

        self.assertEqual(
            events["direction"].tolist(),
            ["bullish", "bearish", "bullish"],
        )

        self.assertEqual(
            events["confirmation_index"].tolist(),
            [2, 4, 7],
        )

    def test_small_moves_below_threshold(self):
        events = self.detect(
            [100, 100.1, 100.2, 100.3, 100.4],
            min_atr_fraction=4.0,
        )

        self.assertTrue(events.empty)

    def test_atr_warmup_prevents_detection(self):
        candles = make_candles([
            100, 101, 102, 103,
        ])

        events = detect_directional_starts(
            candles,
            atr_period=14,
        )

        self.assertTrue(events.empty)

    def test_gap_does_not_join_streaks(self):
        candles = make_candles(
            [100, 100, 101, 102, 103, 103],
            gap_after=2,
        )

        events = detect_directional_starts(
            candles,
            atr_period=2,
        )

        self.assertTrue(events.empty)

    def test_separate_events_after_gap(self):
        candles = make_candles(
            [
                100, 101, 102, 103, 104,
                104, 103, 102, 101, 100,
            ],
            gap_after=4,
        )

        events = detect_directional_starts(
            candles,
            atr_period=3,
        )

        self.assertEqual(
            events["direction"].tolist(),
            ["bullish", "bearish"],
        )

        self.assertEqual(
            events["segment_id"].tolist(),
            [1, 2],
        )

    def test_empty_results_have_expected_columns(self):
        events = self.detect([100] * 20)

        self.assertTrue(events.empty)

        self.assertEqual(
            events.columns.tolist(),
            START_COLUMNS,
        )

    def test_invalid_threshold_rejected(self):
        candles = make_candles([
            100, 101, 102, 103,
        ])

        invalid_values = [
            0,
            -0.5,
            float("nan"),
            float("inf"),
            True,
            "0.5",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    detect_directional_starts(
                        candles,
                        atr_period=3,
                        min_atr_fraction=value,
                    )

    def test_original_candles_not_modified(self):
        candles = make_candles([
            100, 101, 102, 103, 104,
        ])

        original = candles.copy(deep=True)

        detect_directional_starts(
            candles,
            atr_period=3,
        )

        pd.testing.assert_frame_equal(
            candles,
            original,
        )


if __name__ == "__main__":
    unittest.main()
