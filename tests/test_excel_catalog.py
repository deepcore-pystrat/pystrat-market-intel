import os

import pandas as pd
import pytest

from market_intel_pystrat.data.loaders.excel_loader import build_excel_provider

DATA_DIR = os.environ.get("MARKET_INTEL_DATA_DIR")

pytestmark = pytest.mark.skipif(
    DATA_DIR is None, reason="MARKET_INTEL_DATA_DIR not set"
)


def test_all_datasets_load():
    provider = build_excel_provider(DATA_DIR)
    for key in provider.list_instruments():
        frame = provider.get_data(key)
        assert isinstance(frame, pd.DataFrame)
        assert len(frame) > 0
        assert frame.index.is_monotonic_increasing


def test_expected_keys():
    provider = build_excel_provider(DATA_DIR)
    assert provider.list_instruments() == sorted([
        "SB11", "ARBC", "RBST", "CORN",
        "BASIS_VHP", "BASIS_THP", "BASIS_CORN_ARG", "BASIS_CORN_BRZ",
        "BASIS_COFFEE_ARBC", "BASIS_COFFEE_RBST",
    ])