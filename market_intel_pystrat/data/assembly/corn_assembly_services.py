from __future__ import annotations

from typing import Optional

import pandas as pd

from pystrat.context.context_data import Context
from pystrat.data_source.core import schema
from pystrat.domain.clock.clock_services import (
    align_dataframe_to_clock,
    align_to_clock,
    build_from_index,
    slice_window,
)
from pystrat.domain.enum import AssetClass, ContractType
from pystrat.domain.market.core.spec_data import InstrumentId, InstrumentSpec

from market_intel_pystrat.data.profile_inputs_data import (
    CORN_KEY,
    ProfileInputs,
    SPOT_ARG_COLUMN,
    SPOT_BRZ_COLUMN,
    SPREAD_COLUMN,
)
from pystrat.features.features_services import mid_from_sparse_quotes

def corn_spec() -> InstrumentSpec:
    """Corn futures spec, legacy notional accounting: multiplier 1, unit steps."""
    return InstrumentSpec(
        id=InstrumentId(symbol="CORN", venue="CBOT"),
        asset_class=AssetClass.COMMODITY,
        contract_type=ContractType.FUTURE,
        quote_currency="USD",
        price_tick=0.01,
        quantity_step=1.0,
        contract_multiplier=1.0,
    )


def assemble_corn_inputs(
    ohlcv: pd.DataFrame,
    arg: pd.DataFrame,
    brz: pd.DataFrame,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> ProfileInputs:
    """Build corn ProfileInputs: spot mids (ARG/BRZ) and their spread on the futures clock.

    Sparse spot quotes are mid-repaired then forward-filled onto the CORN
    futures trading days.
    """
    ohlcv = slice_window(ohlcv, start, end)
    arg = slice_window(arg, start, end)
    brz = slice_window(brz, start, end)

    arg_mid = mid_from_sparse_quotes(arg[schema.BID], arg[schema.OFFER])
    brz_mid = mid_from_sparse_quotes(brz[schema.BID], brz[schema.OFFER])

    # arg_mid = mid(arg[schema.BID], arg[schema.OFFER]).dropna()
    # brz_mid = mid(brz[schema.BID], brz[schema.OFFER]).dropna()
    # arg_mid = mid(arg[schema.BID], arg[schema.OFFER])
    # brz_mid = mid(brz[schema.BID], brz[schema.OFFER])


    clock = build_from_index(ohlcv.index)
    arg_aligned = align_to_clock(arg_mid, clock, method="ffill")
    brz_aligned = align_to_clock(brz_mid, clock, method="ffill")
    feature_frame = pd.DataFrame(
        {
            SPOT_ARG_COLUMN: arg_aligned,
            SPOT_BRZ_COLUMN: brz_aligned,
            SPREAD_COLUMN: arg_aligned - brz_aligned,
        }
    )

    context = Context(clock=clock, frames={CORN_KEY: feature_frame})
    price_frames = {CORN_KEY: align_dataframe_to_clock(ohlcv, clock, method=None)}
    specs = {CORN_KEY: corn_spec()}

    return ProfileInputs(context=context, price_frames=price_frames, specs=specs)