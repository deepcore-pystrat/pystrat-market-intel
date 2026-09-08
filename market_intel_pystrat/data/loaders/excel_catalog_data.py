from __future__ import annotations

from market_intel_pystrat.data.profile_inputs_data import (
    BASIS_CORN_ARG_KEY,
    BASIS_CORN_BRZ_KEY,
    BASIS_THP_KEY,
    BASIS_VHP_KEY,
    CORN_KEY,
    SB11_KEY,
)


FUTURES_FILES = {
    SB11_KEY: "data_futures_sb11.xlsx",
    "ARBC": "data_futures_arabica.xlsx",
    "RBST": "data_futures_robusta.xlsx",
    CORN_KEY: "data_futures_corn.xlsx",
}


BASIS_MONO_FILES = {
    BASIS_VHP_KEY: "data_spot_VHP.xlsx",
    BASIS_THP_KEY: "data_spot_THP.xlsx",
    BASIS_CORN_ARG_KEY: "data_spot_corn_arg.xlsx",
    BASIS_CORN_BRZ_KEY: "data_spot_corn_brz.xlsx",
}

COFFEE_BASIS_FILE = "data_spot_coffee.xlsx"
COFFEE_BASIS_SHEETS = {
    "BASIS_COFFEE_ARBC": "Coffee Arabica",
    "BASIS_COFFEE_RBST": "Coffee Robusta",
}
REGIME_FILES = {
    "HMM_CORN": "spot_hmm_state_feed_test.csv",
}