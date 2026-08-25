from __future__ import annotations

# IBKR continuous-futures contracts: asset code -> (symbol, exchange).
# RC (robusta) trades under symbol "D" on ICEEUSOFT; ZC (corn) on CBOT.
IBKR_CONTRACTS = {
    "KC": ("KC", "NYBOT"),
    "SB": ("SB", "NYBOT"),
    "RC": ("D", "ICEEUSOFT"),
    "ZC": ("ZC", "CBOT"),
}

# Asset code -> `name` value in the futures table (see deepcore_db_data).
IBKR_TO_DB_NAME = {
    "KC": "arabica",
    "SB": "sb11",
    "RC": "robusta",
    "ZC": "corn",
}

# ZC included: daily ingestion populates corn going forward; the history
# must be backfilled once with a long duration (see fetch_and_upsert).
DEFAULT_ASSETS = ("KC", "SB", "RC", "ZC")

# DB stores prices in cents (13.92 -> 1392); mirror of FUTURES_PRICE_DIVISOR.
PRICE_MULTIPLIER = 100

SELECT_EXISTING_DATES_QUERY = """
    SELECT date
    FROM public.data_market_intelligence_futures
    WHERE name = %s AND date >= %s
"""

INSERT_FUTURES_QUERY = """
    INSERT INTO public.data_market_intelligence_futures
        (name, date, open, high, low, close, volume, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

UPDATE_FUTURES_QUERY = """
    UPDATE public.data_market_intelligence_futures
    SET open = %s, high = %s, low = %s, close = %s, volume = %s, updated_at = %s
    WHERE name = %s AND date = %s
"""
