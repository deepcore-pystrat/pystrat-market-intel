from __future__ import annotations

from typing import Optional

from pystrat.data_source.connectors.postgres_connector_data import PostgresConfig
from pystrat.data_source.connectors.postgres_connector_services import fetch_frame
from pystrat.data_source.providers.postgres_provider import FetchFn, PostgresProvider
from market_intel_pystrat.data.deepcore_db.deepcore_db_services import SPOT_ASSET_IDS, COFFEE_SPOT_ASSET_IDS

from market_intel_pystrat.data.deepcore_db.deepcore_db_services import (
    coffee_spot_source,
    futures_source,
    load_deepcore_config,
    spot_source,
)
from market_intel_pystrat.data.profile_inputs_data import (
    BASIS_CORN_ARG_KEY,
    BASIS_CORN_BRZ_KEY,
    BASIS_THP_KEY,
    BASIS_VHP_KEY,
    CORN_KEY,
    ProfileInputs,
    SB11_KEY,
)
from market_intel_pystrat.data.assembly.sb11_assembly_services import assemble_sb11_basis_inputs
from market_intel_pystrat.data.assembly.corn_assembly_services import assemble_corn_inputs



def load_sb11_basis_inputs(
    config: Optional[PostgresConfig] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> ProfileInputs:
    """SB11 ProfileInputs from the DeepCore DB (config from .env when omitted)."""
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


def load_corn_inputs(
    config: Optional[PostgresConfig] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    *,
    fetch: FetchFn = fetch_frame,
) -> ProfileInputs:
    """Corn ProfileInputs from the DeepCore DB (config from .env when omitted).

    Spots CORN_ARG/CORN_BRZ are populated; CORN futures are expected in the
    shared futures table but are NOT populated yet — this fails until they are.
    `fetch` is injectable so the chain can be tested without a live DB.
    """
    if config is None:
        config = load_deepcore_config()

    provider = PostgresProvider(
        config=config,
        sources={
            CORN_KEY: futures_source("CORN"),
            BASIS_CORN_ARG_KEY: spot_source("CORN_ARG"),
            BASIS_CORN_BRZ_KEY: spot_source("CORN_BRZ"),
        },
        fetch=fetch,
    )

    return assemble_corn_inputs(
        ohlcv=provider.get_data(CORN_KEY),
        arg=provider.get_data(BASIS_CORN_ARG_KEY),
        brz=provider.get_data(BASIS_CORN_BRZ_KEY),
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