from __future__ import annotations

from typing import Optional

from pystrat.data_source.connectors.postgres_connector_data import PostgresConfig
from pystrat.data_source.providers.postgres_provider import PostgresProvider
from market_intel_pystrat.data.deepcore_db.deepcore_db_services import SPOT_ASSET_IDS, COFFEE_SPOT_ASSET_IDS

from market_intel_pystrat.data.deepcore_db.deepcore_db_services import (
    coffee_spot_source,
    futures_source,
    load_deepcore_config,
    spot_source,
)
from market_intel_pystrat.data.profile_inputs_data import (
    BASIS_THP_KEY,
    BASIS_VHP_KEY,
    ProfileInputs,
    SB11_KEY,
)
from market_intel_pystrat.data.assembly.sb11_assembly_services import assemble_sb11_basis_inputs



def load_sb11_basis_inputs(
    config: Optional[PostgresConfig] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> ProfileInputs:

    if config is None:
        config = load_deepcore_config()

    provider = PostgresProvider(
        config=config,
        sources={
            SB11_KEY: futures_source("SB11"),
            BASIS_VHP_KEY: spot_source("VHP"),
            BASIS_THP_KEY: spot_source("THP"),
        },
    )

    return assemble_sb11_basis_inputs(
        ohlcv=provider.get_data(SB11_KEY),
        vhp=provider.get_data(BASIS_VHP_KEY),
        thp=provider.get_data(BASIS_THP_KEY),
        start=start,
        end=end,
    )

def build_postgres_provider(config: Optional[PostgresConfig] = None) -> PostgresProvider:
    """Build a PostgresProvider over every DeepCore dataset (lazy per-key).

    Keys mirror the Excel catalog so both providers are interchangeable.
    CORN futures is declared but empty until the DB is populated.
    """
    if config is None:
        config = load_deepcore_config()
    sources = {key: futures_source(key) for key in ("SB11", "ARBC", "RBST", "CORN")}
    sources.update({f"BASIS_{key}": spot_source(key) for key in SPOT_ASSET_IDS})
    sources.update({f"BASIS_{key}": coffee_spot_source(key) for key in COFFEE_SPOT_ASSET_IDS})
    return PostgresProvider(config=config, sources=sources)