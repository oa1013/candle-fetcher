import unittest
import pandas as pd

from src.data_quality import (
    validate_timestamps,
    detect_candle_gaps,
    validate_session_coverage,
)

class TestDataQuality(unittest.TestCase):

    def test_duplicate_timestamps(self):
        """Detect duplicate candle timestamps."""

        candles = pd.DataFrame({
            "datetime": [
                "2025-01-02 14:10:00+00:00",
                "2025-01-02 14:11:00+00:00",
                "2025-01-02 14:11:00+00:00",
                "2025-01-02 14:12:00+00:00",
            ]
        })

        result = validate_timestamps(candles)

        self.assertEqual(result["total_candles"], 4)
        self.assertEqual(result["unique_timestamps"], 3)
        self.assertEqual(result["duplicate_rows"], 2)
        self.assertTrue(result["is_chronologically_sorted"])
        self.assertEqual(result["backward_movements"], 0)

    def test_missing_candle_detection(self):
        """Detect a missing 1-minute candle."""

        candles = pd.DataFrame({
            "datetime": [
                "2025-01-02 14:10:00+00:00",
                "2025-01-02 14:11:00+00:00",
                "2025-01-02 14:13:00+00:00",
                "2025-01-02 14:14:00+00:00",
            ]
        })

        gaps = detect_candle_gaps(candles)

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps.iloc[0]["gap_minutes"], 2.0)
        self.assertEqual(gaps.iloc[0]["missing_intervals"], 1)

    def test_complete_new_york_session(self):
        """Verify a complete New York session has 200 candles."""

        timestamps = pd.date_range(
            "2025-01-02 09:10",
            periods=200,
            freq="1min",
            tz="America/New_York",
        )

        candles = pd.DataFrame({
            "datetime": timestamps.tz_convert("UTC")
        })

        result = validate_session_coverage(
            candles,
            session_name="new_york",
            trading_date="2025-01-02",
        )

        self.assertEqual(result["expected_candles"], 200)
        self.assertEqual(result["recorded_candles"], 200)
        self.assertEqual(result["missing_candles"], 0)
        self.assertEqual(result["duplicate_candles"], 0)

        self.assertTrue(result["first_candle_matches"])
        self.assertTrue(result["last_candle_matches"])
        self.assertTrue(result["is_complete"])

    def test_incomplete_new_york_session(self):
        """Detect a missing candle within New York trading hours."""

        timestamps = pd.date_range(
            "2025-01-02 09:10",
            periods=200,
            freq="1min",
            tz="America/New_York",
        )

        # Remove one candle from the middle of the session.
        timestamps = timestamps.delete(50)

        candles = pd.DataFrame({
            "datetime": timestamps.tz_convert("UTC")
        })

        result = validate_session_coverage(
            candles,
            session_name="new_york",
            trading_date="2025-01-02",
        )

        self.assertEqual(result["expected_candles"], 200)
        self.assertEqual(result["recorded_candles"], 199)
        self.assertEqual(result["missing_candles"], 1)
        self.assertEqual(result["duplicate_candles"], 0)

        self.assertTrue(result["first_candle_matches"])
        self.assertTrue(result["last_candle_matches"])
        self.assertFalse(result["is_complete"])

    def test_duplicate_candles_in_session(self):
        """Detect duplicate timestamps within a trading session."""

        timestamps = pd.date_range(
            "2025-01-02 09:10",
            periods=200,
            freq="1min",
            tz="America/New_York",
        )

        # Remove one candle and duplicate another.
        timestamps = timestamps.delete(50).append(
            pd.DatetimeIndex([timestamps[49]])
        )

        candles = pd.DataFrame({
            "datetime": timestamps.tz_convert("UTC")
        })

        result = validate_session_coverage(
            candles,
            session_name="new_york",
            trading_date="2025-01-02",
        )

        self.assertEqual(result["expected_candles"], 200)
        self.assertEqual(result["recorded_candles"], 200)
        self.assertEqual(result["missing_candles"], 1)
        self.assertEqual(result["duplicate_candles"], 2)
        self.assertFalse(result["is_complete"])

    def test_asia_reference_window(self):
        """Validate Asia's observed 10:05 reference window."""

        timestamps = pd.date_range(
            "2025-01-02 09:00",
            periods=180,
            freq="1min",
            tz="Asia/Tokyo",
        )

        candles = pd.DataFrame({
            "datetime": timestamps.tz_convert("UTC")
        })

        result = validate_session_coverage(
            candles,
            session_name="asia",
            trading_date="2025-01-02",
            reference_start="10:05",
        )

        self.assertEqual(result["expected_candles"], 115)
        self.assertEqual(result["recorded_candles"], 115)
        self.assertEqual(result["missing_candles"], 0)
        self.assertEqual(result["duplicate_candles"], 0)

        self.assertTrue(result["first_candle_matches"])
        self.assertTrue(result["last_candle_matches"])
        self.assertTrue(result["is_complete"])

    def test_invalid_reference_window(self):
        """Reject reference times after a session closes."""

        candles = pd.DataFrame({
            "datetime": ["2025-01-02 15:00:00+00:00"]
        })

        with self.assertRaisesRegex(
            ValueError,
            "Reference start time must be earlier",
        ):
            validate_session_coverage(
                candles,
                session_name="new_york",
                trading_date="2025-01-02",
                reference_start="13:00",
            )