"""Smoke test for the SB11 basis Excel loader.

Skipped unless MARKET_INTEL_DATA_DIR points at the pystrat data folder
(e.g. .../pystrat_repo/pystrat/data), since the real Excel files are not
committed to this repo.
"""
import os
from pathlib import Path

import pytest

from market_intel_pystrat.data.profile_inputs_data import BASIS_THP_COLUMN, BASIS_VHP_COLUMN, SB11_KEY
from market_intel_pystrat.data.loaders.excel_loader import load_sb11_basis_inputs


_DATA_DIR = os.environ.get("MARKET_INTEL_DATA_DIR")


@pytest.mark.skipif(
    not _DATA_DIR, reason="set MARKET_INTEL_DATA_DIR to the pystrat data folder"
)
def test_load_sb11_basis_inputs_smoke():
    inputs = load_sb11_basis_inputs(Path(_DATA_DIR))

    ctx = inputs.context
    assert SB11_KEY in ctx.frames
    frame = ctx.frames[SB11_KEY]
    assert BASIS_VHP_COLUMN in frame.columns
    assert BASIS_THP_COLUMN in frame.columns
    assert frame.index.equals(ctx.clock.index)

    prices = inputs.price_frames[SB11_KEY]
    assert prices.index.equals(ctx.clock.index)
    assert len(ctx.clock.index) > 0

    assert SB11_KEY in inputs.specs