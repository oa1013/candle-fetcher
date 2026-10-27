from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DASHBOARD_PATH = (
    PROJECT_ROOT / "apps" / "candle_fetcher_v2.py"
)


class TestV2DashboardNavigation(unittest.TestCase):

    def test_all_eight_runner_pages(self):

        pages = [
            "New York Runner",
            "London Runner",
            "Asia Runner",
            "All Sessions Runner",
            "CSV Comparison Runner",
            "Period Regime Finder",
            "Volatility Jump Runner",
            "Daily Session Range Analyzer",
        ]

        app = AppTest.from_file(
            str(DASHBOARD_PATH),
            default_timeout=60,
        ).run()

        self.assertEqual(
            len(app.exception),
            0,
            "Dashboard failed to launch.",
        )

        print("\nPASS: Dashboard launches")

        for page in pages:

            with self.subTest(page=page):

                app.button(
                    key=f"runner_{page}"
                ).click().run()

                self.assertEqual(
                    len(app.exception),
                    0,
                    f"{page} failed to load.",
                )

                self.assertEqual(
                    app.session_state["selected_page"],
                    page,
                )

                print(f"PASS: {page}")

        print(
            "\nSUCCESS: All eight dashboard pages passed"
        )


if __name__ == "__main__":
    unittest.main()
