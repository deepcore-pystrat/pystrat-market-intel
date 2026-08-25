"""Offline test of the corn postgres chain: fake fetch, no DB needed.

Validates query routing, DB-format parsing (prices in cents) and assembly,
so that only real-data checks remain once CORN futures are populated.
"""
import pandas as pd

from pystrat.data_source.connectors.postgres_connector_data import PostgresConfig

from market_intel_pystrat.data.deepcore_db.deepcore_db_data import (
    FUTURES_QUERY,
    SPOT_ASSET_IDS,
)
from market_intel_pystrat.data.loaders.postgres_loader import load_corn_inputs
from market_intel_pystrat.data.profile_inputs_data import (
    CORN_KEY,
    SPOT_ARG_COLUMN,
    SPOT_BRZ_COLUMN,
    SPREAD_COLUMN,
)

_CONFIG = PostgresConfig(host="h", database="d", username="u", password="p")
_DATES = pd.date_range("2024-01-01", periods=10, freq="B")

_COMMODITY_TO_SPOT = {v["data_commodity_id"]: k for k, v in SPOT_ASSET_IDS.items()}


def _fake_fetch(config: PostgresConfig, query: str, params) -> pd.DataFrame:
    """Return raw frames shaped like the DB (futures in cents, spots bid/offer)."""
    if query == FUTURES_QUERY:
        assert params == ("corn",)
        return pd.DataFrame({
            "date": _DATES,
            "open": 40_000.0,
            "high": 41_000.0,
            "low": 39_500.0,
            "close": [40_000.0 + 100.0 * i for i in range(len(_DATES))],
            "volume": 100,
        })
    spot = _COMMODITY_TO_SPOT[params[0]]
    base = 10.0 if spot == "CORN_ARG" else 5.0
    return pd.DataFrame({"date": _DATES, "bid": base, "offer": base + 1.0})


def test_load_corn_inputs_offline_chain():
    inputs = load_corn_inputs(config=_CONFIG, fetch=_fake_fetch)

    frame = inputs.context.frames[CORN_KEY]
    assert list(frame.columns) == [SPOT_ARG_COLUMN, SPOT_BRZ_COLUMN, SPREAD_COLUMN]
    assert len(frame) == len(_DATES)

    # futures prices rescaled from DB cents (40_000 -> 400.0)
    close = inputs.price_frames[CORN_KEY]["close"]
    assert close.iloc[0] == 400.0

    # spread = ARG mid (10.5) - BRZ mid (5.5)
    assert frame[SPREAD_COLUMN].iloc[-1] == 5.0

    assert len(inputs.price_frames[CORN_KEY]) == len(inputs.context.clock.index)
    assert inputs.specs[CORN_KEY].contract_multiplier == 1.0


def test_load_corn_inputs_respects_window():
    inputs = load_corn_inputs(
        config=_CONFIG, start="2024-01-03", end="2024-01-08", fetch=_fake_fetch
    )
    index = inputs.context.clock.index
    assert index[0] >= pd.Timestamp("2024-01-03", tz="UTC")
    assert index[-1] <= pd.Timestamp("2024-01-08", tz="UTC")
