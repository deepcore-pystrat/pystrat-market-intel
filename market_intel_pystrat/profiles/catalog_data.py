from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable, Optional, Union, Tuple

from market_intel_pystrat.data.profile_inputs_data import ProfileInputs
from market_intel_pystrat.data.loaders.excel_loader import (
    load_corn_inputs,
    load_sb11_basis_inputs as load_sb11_basis_inputs_excel,
)
from market_intel_pystrat.data.loaders.postgres_loader import (
    load_sb11_basis_inputs as load_sb11_basis_inputs_postgres,
)
from market_intel_pystrat.profiles.profile_data import MarketIntelProfile

from market_intel_pystrat.profiles.sugar_profiles.legacy import sb11_zscore, sb11_rsi, sb11_rsi_fut
# insert new sugar profiles import here

from market_intel_pystrat.profiles.corn_profiles import (
    corn_arg_zscore,
    corn_brz_zscore,
    corn_spread_zscore,
    save_corn_brz_full_history
)
from pystrat.strategy.core.targets.targets_data import Targets
from pystrat.strategy.core.targets.targets_services import unanimous_merge, majority_merge

from pystrat.strategy.core.targets.targets_services import last_flip_majority_merge

@dataclass(frozen=True)
class ProfileEntry:

    build_profile: Callable[[], MarketIntelProfile]
    load_inputs_excel: Callable[[Union[str, Path]], ProfileInputs]
    load_inputs_postgres: Optional[Callable[[], ProfileInputs]] = None


REGISTRY = {
    "sb11_zscore": ProfileEntry(
        sb11_zscore.profile,
        partial(load_sb11_basis_inputs_excel,start=sb11_zscore.DATA_START, end=sb11_zscore.DATA_END),
        partial(load_sb11_basis_inputs_postgres,start=sb11_zscore.DATA_START, end=sb11_zscore.DATA_END),
    ),
    "sb11_rsi": ProfileEntry(
        sb11_rsi.profile,
        partial(load_sb11_basis_inputs_excel,start=sb11_rsi.DATA_START, end=sb11_rsi.DATA_END),
        partial(load_sb11_basis_inputs_postgres,start=sb11_rsi.DATA_START, end=sb11_rsi.DATA_END),
    ),
    "sb11_rsi_fut": ProfileEntry(
        sb11_rsi_fut.profile,
        partial(load_sb11_basis_inputs_excel,start=sb11_rsi_fut.DATA_START, end=sb11_rsi_fut.DATA_END),
        partial(load_sb11_basis_inputs_postgres,start=sb11_rsi_fut.DATA_START, end=sb11_rsi_fut.DATA_END),
    ),
    # Corn futures are not in the DeepCore DB yet: excel only.
    # ADD postgres partial functions when corn futures are added to DeepCore DB.
    "corn_arg_zscore": ProfileEntry(
        corn_arg_zscore.profile,
        partial(load_corn_inputs, start=corn_arg_zscore.DATA_START, end=corn_arg_zscore.DATA_END),
    ),
    "corn_brz_zscore": ProfileEntry(
        corn_brz_zscore.profile,
        partial(load_corn_inputs, start=corn_brz_zscore.DATA_START, end=corn_brz_zscore.DATA_END),
    ),
    "save_corn_brz_full_history": ProfileEntry(
        save_corn_brz_full_history.profile,
        partial(load_corn_inputs, start=save_corn_brz_full_history.DATA_START, end=save_corn_brz_full_history.DATA_END),
    ),
    "corn_spread_zscore": ProfileEntry(
        corn_spread_zscore.profile,
        partial(load_corn_inputs, start=corn_spread_zscore.DATA_START, end=corn_spread_zscore.DATA_END),
    ),
}


@dataclass(frozen=True)
class FusionEntry:
    components: Tuple[str, ...]  
    combine_factory : Callable[[], Callable[..., Targets]]
    inputs_from: str

FUSIONS = {
    "corn_fusion": FusionEntry(
        components=("corn_arg_zscore", "corn_brz_zscore", "corn_spread_zscore"),
        combine_factory=lambda: unanimous_merge,
        inputs_from="corn_spread_zscore",
    ),
    "corn_fusion_majority": FusionEntry(
        components=("corn_arg_zscore", "corn_brz_zscore", "corn_spread_zscore"),
        combine_factory=lambda : majority_merge,
        inputs_from="corn_spread_zscore",
    ),
    "corn_fusion_lastflip": FusionEntry(
        components=("corn_arg_zscore", "corn_spread_zscore"),
        combine_factory=last_flip_majority_merge,
        inputs_from="corn_spread_zscore",
    ),
}