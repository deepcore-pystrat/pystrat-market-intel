from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple, Union

import pandas as pd

from pystrat.data_source.connectors.postgres_connector_data import PostgresConfig
from pystrat.data_source.connectors.postgres_connector_services import (
    execute_statement,
    fetch_frame,
)

from market_intel_pystrat.data.deepcore_db.deepcore_db_services import (
    DEFAULT_ENV_PATH,
    load_deepcore_config,
)
from market_intel_pystrat.data.ibkr.ibkr_data import (
    DEFAULT_ASSETS,
    IBKR_CONTRACTS,
    IBKR_TO_DB_NAME,
    INSERT_FUTURES_QUERY,
    PRICE_MULTIPLIER,
    SELECT_EXISTING_DATES_QUERY,
    UPDATE_FUTURES_QUERY,
)


def _require_ib_insync():
    try:
        import ib_insync
        return ib_insync
    except ImportError as exc:
        raise ImportError(
            "ib_insync is required for IBKR ingestion. "
            "Install it with: pip install market_intel_pystrat[ingest]"
        ) from exc


def load_gateway_address(env_path: Optional[Union[str, Path]] = None) -> Tuple[str, int]:
    """Read the IB Gateway host/port from a .env file and/or environment variables.

    Looks for IBGATEWAY_HOST and IBGATEWAY_PORT; .env values override the environment.
    """
    from dotenv import dotenv_values

    values = dict(os.environ)
    path = Path(env_path) if env_path is not None else DEFAULT_ENV_PATH
    if path.exists():
        values.update({k: v for k, v in dotenv_values(path).items() if v is not None})

    missing = [k for k in ("IBGATEWAY_HOST", "IBGATEWAY_PORT") if not values.get(k)]
    if missing:
        raise ValueError(
            f"Missing IB Gateway settings {missing}; "
            f"set them in {path} or as environment variables."
        )
    return values["IBGATEWAY_HOST"], int(values["IBGATEWAY_PORT"])


def to_db_cents(value: float) -> str:
    """Price to the DB storage convention: string of integer cents (13.92 -> '1392')."""
    return str(int(round(float(value) * PRICE_MULTIPLIER)))


def normalize_daily_bars(bars: pd.DataFrame) -> pd.DataFrame:
    """Raw IBKR daily bars -> one clean row per date.

    Coerces `date` to datetime.date, drops rows without a close, deduplicates
    by date (last wins) and sorts. Raises if a required column is missing.
    """
    required = ("date", "open", "high", "low", "close", "volume")
    missing = [c for c in required if c not in bars.columns]
    if missing:
        raise ValueError(f"bars missing required column(s): {missing}. Got: {list(bars.columns)}")

    out = bars.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.date
    out = out.dropna(subset=["close"])
    out = out.drop_duplicates(subset=["date"], keep="last").sort_values("date")
    return out.reset_index(drop=True)


def upsert_futures_bars(
    config: PostgresConfig,
    db_name: str,
    bars: pd.DataFrame,
    *,
    fetch=fetch_frame,
    execute=execute_statement,
) -> Tuple[int, int]:
    """Upsert daily bars for one futures family; returns (inserted, updated) counts.

    Existing (name, date) rows are detected with ONE query then updated in
    batch; new dates are inserted in batch. Prices are stored in cents (str),
    mirroring the legacy convention. `fetch`/`execute` are injectable so the
    logic can be tested without a live DB.
    """
    bars = normalize_daily_bars(bars)
    if bars.empty:
        return (0, 0)

    existing = fetch(config, SELECT_EXISTING_DATES_QUERY, (db_name, str(bars["date"].iloc[0])))
    existing_dates = (
        set(pd.to_datetime(existing["date"]).dt.date) if not existing.empty else set()
    )

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    insert_rows, update_rows = [], []

    for _, row in bars.iterrows():
        date = str(row["date"])
        open_, high = to_db_cents(row["open"]), to_db_cents(row["high"])
        low, close = to_db_cents(row["low"]), to_db_cents(row["close"])
        volume = str(int(row["volume"]))

        if row["date"] in existing_dates:
            update_rows.append((open_, high, low, close, volume, now, db_name, date))
        else:
            insert_rows.append((db_name, date, open_, high, low, close, volume, now, now))

    if insert_rows:
        execute(config, INSERT_FUTURES_QUERY, insert_rows)
    if update_rows:
        execute(config, UPDATE_FUTURES_QUERY, update_rows)
    return (len(insert_rows), len(update_rows))


def fetch_daily_history(ib, asset: str, duration: str = "2 D") -> pd.DataFrame:
    """Fetch daily bars for one asset from a connected ib_insync IB instance."""
    ib_insync = _require_ib_insync()
    if asset not in IBKR_CONTRACTS:
        raise KeyError(f"Unknown IBKR asset '{asset}'. Available: {sorted(IBKR_CONTRACTS)}")

    symbol, exchange = IBKR_CONTRACTS[asset]
    contract = ib_insync.ContFuture(symbol=symbol, exchange=exchange)
    bars = ib.reqHistoricalData(
        contract,
        endDateTime="",
        durationStr=duration,
        barSizeSetting="1 day",
        whatToShow="TRADES",
        useRTH=False,
        formatDate=1,
    )
    return ib_insync.util.df(bars)


def fetch_and_upsert(
    config: Optional[PostgresConfig] = None,
    *,
    assets: Sequence[str] = DEFAULT_ASSETS,
    duration: str = "2 D",
    env_path: Optional[Union[str, Path]] = None,
    client_id: int = 1,
) -> Dict[str, Tuple[int, int]]:
    """Fetch the last `duration` of daily bars from IBKR and upsert them into the DB.

    Returns {asset: (inserted, updated)}. Requires a reachable IB Gateway
    (IBGATEWAY_HOST/PORT) and DB credentials (.env or environment). Use a long
    duration (e.g. '15 Y') once per asset to backfill history.
    """
    ib_insync = _require_ib_insync()
    if config is None:
        config = load_deepcore_config(env_path)
    host, port = load_gateway_address(env_path)

    ib = ib_insync.IB()
    ib.connect(host, port, clientId=client_id)

    results: Dict[str, Tuple[int, int]] = {}
    try:
        for asset in assets:
            db_name = IBKR_TO_DB_NAME[asset]
            bars = fetch_daily_history(ib, asset, duration=duration)
            if bars is None or bars.empty:
                print(f"{asset} ({db_name}) -> no data fetched, skipped")
                results[asset] = (0, 0)
                continue
            inserted, updated = upsert_futures_bars(config, db_name, bars)
            print(f"{asset} ({db_name}) -> {inserted} inserted, {updated} updated")
            results[asset] = (inserted, updated)
    finally:
        ib.disconnect()

    return results
