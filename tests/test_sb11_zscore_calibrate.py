import os
from pathlib import Path

import pytest

_DATA_DIR = os.environ.get("MARKET_INTEL_DATA_DIR")


@pytest.mark.skipif(
    not _DATA_DIR, reason="set MARKET_INTEL_DATA_DIR to the pystrat data folder"
)
def test_sb11_zscore_calibrate_end_to_end(tmp_path):
    from market_intel_pystrat.data.loaders.excel_loader import load_sb11_basis_inputs
    from market_intel_pystrat.jobs.calibrate import calibrate
    from market_intel_pystrat.profiles.sugar_profiles.legacy.sb11_zscore import profile

    inputs = load_sb11_basis_inputs(Path(_DATA_DIR))
    out = tmp_path / "run"
    calibrate(profile(), inputs, out)

    assert (out / "calibration_schedule.json").exists()
    assert (out / "oos_equity.csv").exists()
    assert (out / "manifest.json").exists()