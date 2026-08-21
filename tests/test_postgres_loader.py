"""PostgreSQL loader smoke test (skipped without DeepCore credentials)."""
import pytest

from market_intel_pystrat.data.deepcore_db.deepcore_db_services import (
    load_deepcore_config,
)
from market_intel_pystrat.data.profile_inputs_data import (
    BASIS_THP_COLUMN,
    BASIS_VHP_COLUMN,
    SB11_KEY,
)


def _config_or_none():
    try:
        return load_deepcore_config()
    except (ValueError, ImportError):
        return None


@pytest.mark.skipif(_config_or_none() is None, reason="no DeepCore credentials")
def test_load_sb11_basis_inputs_from_db_smoke():
    from market_intel_pystrat.data.loaders.postgres_loader import load_sb11_basis_inputs

    inputs = load_sb11_basis_inputs()
    frame = inputs.context.frames[SB11_KEY]
    assert BASIS_VHP_COLUMN in frame.columns and BASIS_THP_COLUMN in frame.columns
    assert len(frame) > 1000  # real history, not a truncated fetch
    assert len(inputs.price_frames[SB11_KEY]) == len(inputs.context.clock.index)
    assert inputs.specs[SB11_KEY].contract_multiplier == 1120.0