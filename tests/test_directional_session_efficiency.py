"""
Candle Fetcher — Session Efficiency Regression Tests.

Tests deterministic M1 price paths, New York timezone
handling, complete sessions, missing candles, invalid
data, and input preservation.

No external MT5 connection or historical CSV required.
"""

import unittest

import numpy as np
import pandas as pd

from src.directional_session_efficiency import (
    calculate_ny_session_efficiency,
)


def make_session(day, pattern="trend"):
    """Create 200 deterministic NY morning M1 candles."""

    times = pd.date_range(
        f"{day} 09:10",
        periods=200,
        freq="min",
        tz="America/New_York",
    ).tz_convert("UTC")

    indexes = np.arange(200, dtype=float)

    if pattern == "trend":
        opens = 100.0 + indexes * 0.2
        closes = opens + 0.1

    elif pattern in ("choppy", "roundtrip"):
        closes = 100.0 + (indexes % 2)

        if pattern == "roundtrip":
            closes[-1] = 100.0

        opens = np.concatenate((
            [100.0],
            closes[:-1],
        ))

    elif pattern == "flat":
        opens = np.full(200, 100.0)
        closes = np.full(200, 100.0)

    else:
        raise ValueError("Unknown test pattern.")

    wick = 0.0 if pattern == "flat" else (
        0.25 if pattern != "trend" else 0.05
    )

    return pd.DataFrame({
        "datetime": times,
        "open": opens,
        "high": np.maximum(opens, closes) + wick,
        "low": np.minimum(opens, closes) - wick,
        "close": closes,
    })


class TestDirectionalSessionEfficiency(unittest.TestCase):

    def test_winter_and_summer_sessions(self):
        winter = make_session("2024-01-08")
        summer = make_session("2024-07-24")

        self.assertEqual(
            winter["datetime"].iloc[0],
            pd.Timestamp("2024-01-08 14:10:00+00:00"),
        )

        self.assertEqual(
            summer["datetime"].iloc[0],
            pd.Timestamp("2024-07-24 13:10:00+00:00"),
        )

        candles = pd.concat(
            [winter, summer],
            ignore_index=True,
        )

        result = calculate_ny_session_efficiency(
            candles,
            year=2024,
        )

        self.assertEqual(len(result), 2)

        self.assertEqual(
            result["ny_session_date"].tolist(),
            ["2024-01-08", "2024-07-24"],
        )

        self.assertTrue(
            result["candle_count"].eq(200).all()
        )

    def test_known_trending_path_math(self):
        candles = make_session("2024-01-08")

        result = calculate_ny_session_efficiency(
            candles,
            year=2024,
        ).iloc[0]

        self.assertAlmostEqual(
            result["reconstructed_range"],
            40.0,
            places=8,
        )

        self.assertAlmostEqual(
            result["net_displacement_points"],
            39.9,
            places=8,
        )

        self.assertAlmostEqual(
            result["close_path_points"],
            39.9,
            places=8,
        )

        self.assertAlmostEqual(
            result["net_range_share_pct"],
            99.75,
            places=8,
        )

        self.assertAlmostEqual(
            result["close_path_efficiency_pct"],
            100.0,
            places=8,
        )

    def test_known_choppy_path_math(self):
        candles = make_session(
            "2024-01-08",
            pattern="choppy",
        )

        result = calculate_ny_session_efficiency(
            candles,
            year=2024,
        ).iloc[0]

        self.assertAlmostEqual(
            result["reconstructed_range"],
            1.5,
            places=8,
        )

        self.assertAlmostEqual(
            result["net_displacement_points"],
            1.0,
            places=8,
        )

        self.assertAlmostEqual(
            result["close_path_points"],
            199.0,
            places=8,
        )

        self.assertAlmostEqual(
            result["close_path_efficiency_pct"],
            100.0 / 199.0,
            places=8,
        )

    def test_zero_net_displacement_is_valid(self):
        candles = make_session(
            "2024-01-08",
            pattern="roundtrip",
        )

        result = calculate_ny_session_efficiency(
            candles,
            year=2024,
        ).iloc[0]

        self.assertGreater(
            result["close_path_points"],
            0,
        )

        self.assertEqual(
            result["net_displacement_points"],
            0,
        )

        self.assertEqual(
            result["close_path_efficiency_pct"],
            0,
        )

        self.assertEqual(
            result["net_range_share_pct"],
            0,
        )

    def test_missing_final_candle_rejected(self):
        candles = make_session("2024-01-08")
        candles = candles.iloc[:-1].copy()

        with self.assertRaisesRegex(
            ValueError,
            "Incomplete NY session",
        ):
            calculate_ny_session_efficiency(
                candles,
                year=2024,
            )

    def test_missing_interior_candle_rejected(self):
        candles = make_session("2024-01-08")
        candles = candles.drop(
            index=80,
        ).reset_index(drop=True)

        with self.assertRaisesRegex(
            ValueError,
            "Incomplete NY session",
        ):
            calculate_ny_session_efficiency(
                candles,
                year=2024,
            )

    def test_irregular_candle_spacing_rejected(self):
        candles = make_session("2024-01-08")

        # Preserve 200 rows and session endpoints,
        # but introduce a 30-second timestamp error.
        candles.loc[80, "datetime"] = (
            candles.loc[80, "datetime"]
            + pd.Timedelta(seconds=30)
        )

        with self.assertRaisesRegex(
            ValueError,
            "Nonconsecutive M1 candles",
        ):
            calculate_ny_session_efficiency(
                candles,
                year=2024,
            )

    def test_duplicate_timestamps_rejected(self):
        candles = make_session("2024-01-08")

        candles.loc[80, "datetime"] = (
            candles.loc[79, "datetime"]
        )

        with self.assertRaises(ValueError):
            calculate_ny_session_efficiency(
                candles,
                year=2024,
            )

    def test_naive_timestamps_rejected(self):
        candles = make_session("2024-01-08")

        candles["datetime"] = (
            candles["datetime"].dt.tz_localize(None)
        )

        with self.assertRaises(ValueError):
            calculate_ny_session_efficiency(
                candles,
                year=2024,
            )

    def test_unsorted_timestamps_rejected(self):
        candles = make_session("2024-01-08")

        candles = candles.iloc[::-1].reset_index(
            drop=True
        )

        with self.assertRaises(ValueError):
            calculate_ny_session_efficiency(
                candles,
                year=2024,
            )

    def test_invalid_ohlc_rejected(self):
        candles = make_session("2024-01-08")

        candles.loc[50, "high"] = (
            candles.loc[50, "low"] - 1.0
        )

        with self.assertRaises(ValueError):
            calculate_ny_session_efficiency(
                candles,
                year=2024,
            )

    def test_zero_price_path_rejected(self):
        candles = make_session(
            "2024-01-08",
            pattern="flat",
        )

        with self.assertRaisesRegex(
            ValueError,
            "zero range or zero sampled path",
        ):
            calculate_ny_session_efficiency(
                candles,
                year=2024,
            )

    def test_no_matching_year_rejected(self):
        candles = make_session("2024-01-08")

        with self.assertRaisesRegex(
            ValueError,
            "No candles found",
        ):
            calculate_ny_session_efficiency(
                candles,
                year=2025,
            )

    def test_invalid_session_configuration(self):
        candles = make_session("2024-01-08")

        cases = [
            {"year": True},
            {
                "year": 2024,
                "session_start": "invalid",
            },
            {
                "year": 2024,
                "session_start": "12:30",
                "session_end": "09:10",
            },
            {
                "year": 2024,
                "session_start": "09:10",
                "session_end": "09:10",
            },
        ]

        for settings in cases:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    calculate_ny_session_efficiency(
                        candles,
                        **settings,
                    )

    def test_custom_session_window(self):
        candles = make_session("2024-01-08")

        result = calculate_ny_session_efficiency(
            candles,
            year=2024,
            session_start="09:10",
            session_end="09:15",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result["candle_count"].iloc[0],
            5,
        )

    def test_candles_outside_window_ignored(self):
        candles = make_session("2024-01-08")

        outside = pd.DataFrame({
            "datetime": [
                pd.Timestamp(
                    "2024-01-08 09:09",
                    tz="America/New_York",
                ).tz_convert("UTC"),
                pd.Timestamp(
                    "2024-01-08 12:30",
                    tz="America/New_York",
                ).tz_convert("UTC"),
            ],
            "open": [100.0, 100.0],
            "high": [1000.0, 1000.0],
            "low": [0.0, 0.0],
            "close": [100.0, 100.0],
        })

        extended = pd.concat(
            [candles, outside],
            ignore_index=True,
        ).sort_values(
            "datetime"
        ).reset_index(drop=True)

        original_result = calculate_ny_session_efficiency(
            candles,
            year=2024,
        )

        extended_result = calculate_ny_session_efficiency(
            extended,
            year=2024,
        )

        pd.testing.assert_frame_equal(
            original_result,
            extended_result,
        )

    def test_input_dataframe_not_modified(self):
        candles = make_session("2024-01-08")
        original = candles.copy(deep=True)

        calculate_ny_session_efficiency(
            candles,
            year=2024,
        )

        pd.testing.assert_frame_equal(
            candles,
            original,
        )


if __name__ == "__main__":
    unittest.main()
