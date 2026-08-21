from __future__ import annotations

import json
from pathlib import Path
from typing import Union, Optional

from market_intel_pystrat.jobs.calibrate import calibrate
from market_intel_pystrat.jobs.report import render_run
from market_intel_pystrat.profiles.catalog_data import REGISTRY
from market_intel_pystrat.profiles.catalog_services import load_profile_inputs
from pystrat.research.artifacts.artifacts_services import prune_research_artifacts


def run_calibration(
    name: str,
    out_dir: Union[str, Path],
    data_dir: Optional[Union[str, Path]] = None,
    *,
    source: str = "excel",
) -> Path:
    out_dir = Path(out_dir)
    entry = REGISTRY[name]
    profile = entry.build_profile()
    inputs = load_profile_inputs(entry, source, data_dir)
    context = calibrate(profile, inputs, out_dir, overwrite=True)
    schedule = json.loads((out_dir / "calibration_schedule.json").read_text())
    decision = profile.decision_series(context, schedule) if profile.decision_series else None
    render_run(out_dir, decision=decision)
    prune_research_artifacts(out_dir)
    return out_dir