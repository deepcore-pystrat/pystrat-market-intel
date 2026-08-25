from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from pystrat.data_source.connectors.postgres_connector_data import PostgresConfig
from pystrat.data_source.core import schema
from pystrat.data_source.providers.postgres_provider import PostgresSource

from market_intel_pystrat.data.deepcore_db.deepcore_db_data import (
    COFFEE_SPOT_ASSET_IDS,
    COFFEE_SPOT_QUERY,
    FUTURES_ASSET_NAMES,
    FUTURES_PRICE_DIVISOR,
    FUTURES_QUERY,
    SPOT_ASSET_IDS,
    SPOT_QUERY,
)

DEFAULT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"

_REQUIRED_KEYS = (
    "POSTGRES_HOST",
    "POSTGRES_DATABASE",
    "POSTGRES_USERNAME",
    "POSTGRES_PASSWORD",
)

def load_deepcore_config(env_path : Optional[Union[str, Path]] = None) -> PostgresConfig :
    """Read Postgres settings from a .env file and/or environment variables.

    Looks for POSTGRES_HOST/DATABASE/USERNAME/PASSWORD (+ optional PORT);
    .env values override the environment. Raises if any required key is missing.
    """
    from dotenv import dotenv_values

    values = dict(os.environ)
    path = Path(env_path) if env_path is not None else DEFAULT_ENV_PATH

    if path.exists() :
        values.update(
            {k : v for k, v in dotenv_values(path).items() if v is not None}
        )
    
    missing = [k for k in _REQUIRED_KEYS if not values.get(k)]

    if missing:
        raise ValueError(
            f"Missing DeepCore DB settings {missing}; "
            f"set them in {path} or as environment variables."
        )
    
    return PostgresConfig(
        host=values["POSTGRES_HOST"],
        database=values["POSTGRES_DATABASE"],
        username=values["POSTGRES_USERNAME"],
        password=values["POSTGRES_PASSWORD"],
        port=int(values.get("POSTGRES_PORT", 5432)),
    )


def parse_futures_frame(raw : pd.DataFrame) -> pd.DataFrame :
    """Raw futures rows -> canonical OHLCV bars (prices rescaled from DB cents)."""
    out = raw.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.set_index("date").sort_index()
    out.index.name = None

    for col in schema.OHLCV_COLUMNS:

        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    for col in (schema.OPEN, schema.HIGH, schema.LOW, schema.CLOSE):

        if col in out.columns:
            out[col] = out[col] / FUTURES_PRICE_DIVISOR
            
    schema.validate_bars(out)

    return out


def parse_quotations_frame(raw : pd.DataFrame) -> pd.DataFrame :
    """Raw quotations rows -> canonical bid/offer basis frame (DatetimeIndex)."""
    out = raw.copy()

    out["date"] = pd.to_datetime(out["date"])
    out = out.set_index("date").sort_index()
    out.index.name = None

    out[schema.BID] = pd.to_numeric(out[schema.BID], errors="coerce")
    out[schema.OFFER] = pd.to_numeric(out[schema.OFFER], errors="coerce")
   
    schema.validate_basis(out)
    
    return out


def futures_source(asset_name : str) -> PostgresSource :
    """PostgresSource for one futures family (see FUTURES_ASSET_NAMES)."""
    asset_upper = asset_name.upper()

    if asset_upper not in FUTURES_ASSET_NAMES:
        raise KeyError(
            f"Unknown futures asset '{asset_name}'. "
            f"Available: {sorted(set(FUTURES_ASSET_NAMES))}"
        )
    return PostgresSource(
        query=FUTURES_QUERY,
        params=(FUTURES_ASSET_NAMES[asset_upper],),
        parser=parse_futures_frame,
    )


def spot_source(asset_name : str) -> PostgresSource :
    """PostgresSource for one mono-series spot (see SPOT_ASSET_IDS)."""
    if asset_name not in SPOT_ASSET_IDS:
        raise KeyError(
            f"Unknown spot asset '{asset_name}'. "
            f"Available: {sorted(SPOT_ASSET_IDS)}"
        )
    ids = SPOT_ASSET_IDS[asset_name]
    return PostgresSource(
        query=SPOT_QUERY,
        params=(ids["data_commodity_id"], ids["shipment_period_id"]),
        parser=parse_quotations_frame,
    )


def parse_coffee_frame(raw : pd.DataFrame) -> pd.DataFrame :
    """Raw coffee quotations -> long-form basis (origin, value = bid/offer mid)."""
    out = raw.copy()

    out["date"] = pd.to_datetime(out["date"])
    out = out.set_index("date").sort_index()
    out.index.name = None

    bid = pd.to_numeric(out[schema.BID], errors="coerce")
    offer = pd.to_numeric(out[schema.OFFER], errors="coerce")

    out[schema.VALUE] = 0.5 * (bid.fillna(offer) + offer.fillna(bid))
    out = out[[schema.ORIGIN, schema.VALUE]]

    schema.validate_basis(out)

    return out


def coffee_spot_source(asset_name : str) -> PostgresSource :
    """PostgresSource for one multi-origin coffee spot (see COFFEE_SPOT_ASSET_IDS)."""
    if asset_name not in COFFEE_SPOT_ASSET_IDS:
        raise KeyError(
            f"Unknown coffee spot asset '{asset_name}'. "
            f"Available: {sorted(COFFEE_SPOT_ASSET_IDS)}"
        )
    
    return PostgresSource(
        query=COFFEE_SPOT_QUERY,
        params=(COFFEE_SPOT_ASSET_IDS[asset_name],),
        parser=parse_coffee_frame,
    )