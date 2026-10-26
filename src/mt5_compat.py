
from __future__ import annotations

import os
import sys


# --------------------------------------------------
# Candle Fetcher — Cross-platform MT5 compatibility
# --------------------------------------------------

if sys.platform == "win32":

    # Windows: use the official MetaTrader5 package.
    import MetaTrader5 as mt5

elif sys.platform.startswith("linux"):

    # Linux: connect to MT5 through the Wine bridge.
    from mt5linux import MetaTrader5

    MT5_BRIDGE_HOST = os.environ.get(
        "CANDLE_FETCHER_MT5_HOST",
        "127.0.0.1",
    )

    MT5_BRIDGE_PORT = int(
        os.environ.get(
            "CANDLE_FETCHER_MT5_PORT",
            "18812",
        )
    )

    mt5 = MetaTrader5(
        host=MT5_BRIDGE_HOST,
        port=MT5_BRIDGE_PORT,
    )

else:

    raise RuntimeError(
        f"Unsupported operating system: {sys.platform}"
    )
