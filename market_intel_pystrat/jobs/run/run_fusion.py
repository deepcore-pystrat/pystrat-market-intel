from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from pystrat.engine.recorders import BarTraceRecorder
from pystrat.research.artifacts.artifacts_services import save_schedule_replay
from pystrat.research.calibration.replay.replay_services import replay_fusion_from_schedules

from market_intel_pystrat.profiles.catalog_data import REGISTRY, FUSIONS
from market_intel_pystrat.profiles.catalog_services import load_profile_inputs
from market_intel_pystrat.jobs.report import render_run

def _read_schedule(run_dir: Path) -> dict:
    f = run_dir / "calibration_schedule.json"
    if not f.exists():
        raise FileNotFoundError(f"{f} not found: calibrate this component first")
    return json.loads(f.read_text())


def run_fusion(
        name: str,
        out_dir: Union[str, Path],
        data_dir: Optional[Union[str, Path]] = None,
        *,
        source: str = "excel",
        runs_root: Union[str, Path] = Path("artifacts/runs"),
) -> Path:
    out_dir = Path(out_dir)
    entry = FUSIONS[name]
    profiles = [REGISTRY[c].build_profile() for c in entry.components]
    schedules = [_read_schedule(Path(runs_root) / c) for c in entry.components]

    inputs = load_profile_inputs(REGISTRY[entry.inputs_from], source, data_dir)
    context = inputs.context
    for profile in profiles:
        context = profile.add_features(context)

    lead = profiles[0]
    recorder = BarTraceRecorder()
    replay = replay_fusion_from_schedules(
        schedules,
        [p.build_strategy for p in profiles],
        entry.combine_factory(),
        context,
        inputs.price_frames,
        inputs.specs,
        lead.executor,
        lead.accounting,
        lead.portfolio_factory,
        warmup_bars=max(p.warmup_bars for p in profiles),
        observers=[recorder],
        handoff=lead.handoff,
    )

    save_schedule_replay(
        out_dir,
        schedule={c: s for c, s in zip(entry.components, schedules)},
        oos_replay=replay,
        trace=recorder.frame(),
        specs=inputs.specs,
        manifest={"kind": "fusion", "fusion": name, "components": list(entry.components)},
        overwrite=True,
    )

    render_run(out_dir)

    return out_dir