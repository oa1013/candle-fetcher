"""Regression tests for FTMO-specific MT5 timestamp handling."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pandas as pd

from src.ftmo_time import (
    ftmo_raw_seconds_to_utc,
    utc_to_ftmo_request_clock,
)
from src.mt5_fetcher import fetch_candles_by_range
from src.mt5_compat import mt5


UTC = timezone.utc
NY = ZoneInfo("America/New_York")

TEST_DATES = [
    "2025-01-15",
    "2025-03-10",
    "2025-03-31",
    "2025-07-15",
    "2025-10-24",
    "2025-10-27",
]


def new_york_open(day):
    return datetime.fromisoformat(
        f"{day}T09:30:00"
    ).replace(tzinfo=NY).astimezone(UTC)


def make_rates(start, count, ftmo_clock):
    rows = []

    for index in range(count):
        actual_utc = start + timedelta(minutes=index)

        if ftmo_clock:
            encoded = utc_to_ftmo_request_clock(actual_utc)
        else:
            encoded = actual_utc

        price = 20000.0 + index

        rows.append({
            "time": int(encoded.timestamp()),
            "open": price,
            "high": price + 2.0,
            "low": price - 2.0,
            "close": price + 1.0,
            "tick_volume": 100,
            "spread": 10,
            "real_volume": 0,
        })

    return rows


class TestFTMOTime(unittest.TestCase):

    def test_historical_round_trips(self):
        for day in TEST_DATES:
            with self.subTest(day=day):
                original = new_york_open(day)

                server_clock = utc_to_ftmo_request_clock(
                    original
                )

                recovered = ftmo_raw_seconds_to_utc(
                    pd.Series([int(server_clock.timestamp())])
                ).iloc[0]

                self.assertEqual(
                    recovered,
                    pd.Timestamp(original),
                )

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            utc_to_ftmo_request_clock(
                datetime(2025, 1, 15, 9, 30)
            )

    def test_invalid_dst_times_rejected(self):
        invalid_cases = [
            ("2025-03-30T03:30:00Z", "nonexistent"),
            ("2025-10-26T03:30:00Z", "ambiguous"),
        ]

        for timestamp, expected_message in invalid_cases:
            with self.subTest(timestamp=timestamp):
                raw = int(pd.Timestamp(timestamp).timestamp())

                with self.assertRaises(Exception) as raised:
                    ftmo_raw_seconds_to_utc(
                        pd.Series([raw])
                    )

                message = str(raised.exception).lower()

                self.assertTrue(
                    expected_message in message
                    or (
                        expected_message == "ambiguous"
                        and "cannot infer dst" in message
                    ),
                    f"Unexpected exception: {raised.exception}",
                )

    def test_ftmo_fetch_boundaries(self):
        for day in TEST_DATES:
            with self.subTest(day=day):
                start = new_york_open(day) - timedelta(
                    minutes=3
                )
                end = start + timedelta(minutes=8)

                # Simulate the inclusive MT5 response.
                rates = make_rates(
                    start, count=9, ftmo_clock=True
                )

                with patch(
                    "src.mt5_fetcher.mt5.copy_rates_range",
                    return_value=rates,
                ) as mocked:
                    result = fetch_candles_by_range(
                        symbol="US100.cash",
                        timeframe_mt5=mt5.TIMEFRAME_M1,
                        start_utc=start,
                        end_utc_exclusive=end,
                        chunk_days=1,
                        ftmo_athens_clock=True,
                    )

                args = mocked.call_args.args

                self.assertEqual(
                    args[2],
                    utc_to_ftmo_request_clock(start),
                )
                self.assertEqual(
                    args[3],
                    utc_to_ftmo_request_clock(end),
                )

                self.assertEqual(len(result), 8)
                self.assertEqual(
                    result["datetime"].iloc[0],
                    pd.Timestamp(start),
                )
                self.assertEqual(
                    result["datetime"].iloc[-1],
                    pd.Timestamp(
                        end - timedelta(minutes=1)
                    ),
                )

                self.assertFalse(
                    result["datetime"].duplicated().any()
                )

    def test_standard_utc_mode_unchanged(self):
        start = datetime(
            2025, 7, 15, 13, 27, tzinfo=UTC
        )
        end = start + timedelta(minutes=8)

        rates = make_rates(
            start, count=9, ftmo_clock=False
        )

        with patch(
            "src.mt5_fetcher.mt5.copy_rates_range",
            return_value=rates,
        ) as mocked:
            result = fetch_candles_by_range(
                symbol="US100.cash",
                timeframe_mt5=mt5.TIMEFRAME_M1,
                start_utc=start,
                end_utc_exclusive=end,
                chunk_days=1,
                ftmo_athens_clock=False,
            )

        args = mocked.call_args.args

        self.assertEqual(args[2], start)
        self.assertEqual(args[3], end)
        self.assertEqual(len(result), 8)
        self.assertEqual(
            result["datetime"].iloc[0],
            pd.Timestamp(start),
        )


if __name__ == "__main__":
    unittest.main()
