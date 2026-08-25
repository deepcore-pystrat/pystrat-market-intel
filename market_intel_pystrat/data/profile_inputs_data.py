from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from pystrat.context.context_data import Context
from pystrat.domain.market.core.spec_data import InstrumentSpec

SB11_KEY = "SB11"
FUTURE_CLOSE_COLUMN = "future_close"
BASIS_VHP_KEY = "BASIS_VHP"
BASIS_THP_KEY = "BASIS_THP"
BASIS_VHP_COLUMN = "basis_vhp"
BASIS_THP_COLUMN = "basis_thp"

CORN_KEY = "CORN"
BASIS_CORN_ARG_KEY = "BASIS_CORN_ARG"
BASIS_CORN_BRZ_KEY = "BASIS_CORN_BRZ"
SPOT_ARG_COLUMN = "spot_arg_mid"
SPOT_BRZ_COLUMN = "spot_brz_mid"
SPREAD_COLUMN = "spread"

@dataclass(frozen=True)
class ProfileInputs :
    """Everything a profile needs to run: aligned Context, price frames and specs."""

    context : Context
    price_frames : Mapping[str, pd.DataFrame]
    specs : Mapping[str, InstrumentSpec]