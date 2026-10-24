import unittest
import pandas as pd

from src.range_analysis import (
    calculate_range,
    calculate_daily_ranges,
    calculate_session_ranges,
)


class TestRangeAnalysis(unittest.TestCase):

    def test_calculate_range(self):
        """Test the high, low, and price range calculation."""

        candles = pd.DataFrame({
            "high": [21050.0, 21100.0, 21080.0],
            "low": [21000.0, 21020.0, 21010.0],
        })

        result = calculate_range(candles)

        self.assertEqual(result["high"], 21100.0)
        self.assertEqual(result["low"], 21000.0)
        self.assertEqual(result["range_points"], 100.0)
        self.assertAlmostEqual(
            result["range_percent"],
            0.4762,
            places=4,
        )

    def test_calculate_daily_ranges(self):
        """Test daily high, low and range calculations."""

        candles = pd.DataFrame({
            "datetime": [
                "2025-01-02 10:00:00+00:00",
                "2025-01-02 10:01:00+00:00",
                "2025-01-03 10:00:00+00:00",
                "2025-01-03 10:01:00+00:00",
            ],
            "high": [21050.0, 21100.0, 21200.0, 21250.0],
            "low": [21000.0, 21020.0, 21100.0, 21150.0],
        })

        result = calculate_daily_ranges(candles)

        self.assertEqual(len(result), 2)

        self.assertEqual(result.iloc[0]["range_points"], 100.0)
        self.assertEqual(result.iloc[1]["range_points"], 150.0)

        self.assertEqual(result.iloc[0]["candle_count"], 2)
        self.assertEqual(result.iloc[1]["candle_count"], 2)

    
    def test_new_york_session_range(self):
        """Test New York session filtering and range calculation."""

        candles = pd.DataFrame({
            "datetime": [
                "2025-01-02 14:09:00+00:00",
                "2025-01-02 14:10:00+00:00",
                "2025-01-02 14:11:00+00:00",
                "2025-01-02 17:30:00+00:00",
            ],
            "high": [25000.0, 21100.0, 21150.0, 26000.0],
            "low": [20000.0, 21000.0, 21050.0, 19000.0],
        })

        result = calculate_session_ranges(
            candles,
            session_name="new_york",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["candle_count"], 2)
        self.assertEqual(result.iloc[0]["high"], 21150.0)
        self.assertEqual(result.iloc[0]["low"], 21000.0)
        self.assertEqual(result.iloc[0]["range_points"], 150.0)

    def test_london_session_range(self):
        """Test London session filtering and range calculation."""

        candles = pd.DataFrame({
            "datetime": [
                "2025-01-02 07:59:00+00:00",
                "2025-01-02 08:00:00+00:00",
                "2025-01-02 08:01:00+00:00",
                "2025-01-02 11:00:00+00:00",
            ],
            "high": [25000.0, 21100.0, 21180.0, 26000.0],
            "low": [20000.0, 21000.0, 21050.0, 19000.0],
        })

        result = calculate_session_ranges(
            candles,
            session_name="london",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["candle_count"], 2)
        self.assertEqual(result.iloc[0]["high"], 21180.0)
        self.assertEqual(result.iloc[0]["low"], 21000.0)
        self.assertEqual(result.iloc[0]["range_points"], 180.0)

    def test_asia_session_range(self):
        """Test Asia session filtering and range calculation."""

        candles = pd.DataFrame({
            "datetime": [
                "2025-01-02 23:59:00+00:00",
                "2025-01-03 00:00:00+00:00",
                "2025-01-03 00:01:00+00:00",
                "2025-01-03 03:00:00+00:00",
            ],
            "high": [25000.0, 21100.0, 21170.0, 26000.0],
            "low": [20000.0, 21000.0, 21050.0, 19000.0],
        })

        result = calculate_session_ranges(
            candles,
            session_name="asia",
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["candle_count"], 2)
        self.assertEqual(result.iloc[0]["high"], 21170.0)
        self.assertEqual(result.iloc[0]["low"], 21000.0)
        self.assertEqual(result.iloc[0]["range_points"], 170.0)

