from __future__ import annotations

import pandas as pd
from typing import Optional

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
from pystrat.features.features_services import mid_from_sparse_quotes
from market_intel_pystrat.data.profile_inputs_data import (
    BASIS_THP_COLUMN,
    BASIS_VHP_COLUMN,
    FUTURE_CLOSE_COLUMN,
    ProfileInputs,
    SB11_KEY,
)


def sb11_spec() -> InstrumentSpec:

    return InstrumentSpec(
        id=InstrumentId(symbol="SB11", venue="ICE"),
        asset_class=AssetClass.COMMODITY,
        contract_type=ContractType.FUTURE,
        quote_currency="USD",
        price_tick=0.01,
        quantity_step=1.0,
        contract_multiplier=1120.0,
    )

def assemble_sb11_basis_inputs(
    ohlcv: pd.DataFrame,
    vhp: pd.DataFrame,
    thp: pd.DataFrame,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> ProfileInputs:

    ohlcv = slice_window(ohlcv, start, end)
    vhp = slice_window(vhp, start, end)
    thp = slice_window(thp, start, end)

    vhp_mid = mid_from_sparse_quotes(vhp[schema.BID], vhp[schema.OFFER])
    thp_mid = mid_from_sparse_quotes(thp[schema.BID], thp[schema.OFFER])

    clock = build_from_index(ohlcv.index)
    ohlcv_aligned = align_dataframe_to_clock(ohlcv, clock, method=None)

    feature_frame = pd.DataFrame(
        {
            BASIS_VHP_COLUMN : align_to_clock(vhp_mid, clock, method="ffill"),
            BASIS_THP_COLUMN : align_to_clock(thp_mid, clock, method="ffill"),
            FUTURE_CLOSE_COLUMN : ohlcv_aligned[schema.CLOSE],
        }
    )

    context = Context(clock=clock, frames={SB11_KEY: feature_frame})
    price_frames = {SB11_KEY: ohlcv_aligned}
    specs = {SB11_KEY: sb11_spec()}

    return ProfileInputs(context=context, price_frames=price_frames, specs=specs)