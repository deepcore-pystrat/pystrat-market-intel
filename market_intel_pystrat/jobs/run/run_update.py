from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Union, Optional

from pystrat.engine.recorders import BarTraceRecorder
from pystrat.research.artifacts.artifacts_services import save_schedule_replay
from pystrat.research.calibration.extension.extension_services import extend_calibration
from pystrat.research.calibration.replay.replay_services import replay_from_schedule

from market_intel_pystrat.jobs.report import render_run
from market_intel_pystrat.profiles.catalog_services import load_profile_inputs
from market_intel_pystrat.profiles.catalog_data import REGISTRY

def _read_schedule(run_dir : Path) -> Mapping[str, Any] : 
    """Read the run's saved schedule; empty mapping if none exists yet."""
    f = run_dir / "calibration_schedule.json"
    return json.loads(f.read_text()) if f.exists() else {}


def run_update(
        name : str,
        run_dir : Union[str, Path],
        data_dir : Optional[Union[str, Path]] = None,
        *,
        source : str = "excel",
) -> Path :
    """Extend a run's calibration with newly available folds, then replay and re-render.

    Works from scratch too (empty schedule). The last fold's params are held to
    the end of the data (live-like behaviour between recalibrations).
    """
    run_dir = Path(run_dir)
    entry = REGISTRY[name]
    profile = entry.build_profile()
    inputs = load_profile_inputs(entry, source, data_dir)
    context = profile.add_features(inputs.context)

    old_schedule = _read_schedule(run_dir)

    extension = extend_calibration(
        old_schedule,
        profile.optimizer,
        profile.search_score,
        profile.splitter,
        profile.build_strategy,
        context,
        inputs.price_frames,
        inputs.specs,
        profile.executor,
        profile.accounting,
        profile.portfolio_factory,
        profile.objective,
        profile.selector,
        preparer=profile.preparer,
        warmup_bars=profile.warmup_bars,
        per_fold_search=profile.per_fold_search,
    )

    if not extension.schedule:
        raise ValueError(
            f"no calibration folds available for '{name}': "
            "not enough data to build or extend the schedule"
        )

    recorder = BarTraceRecorder()

    replay = replay_from_schedule(
        extension.schedule, 
        profile.build_strategy, 
        context, 
        inputs.price_frames, 
        inputs.specs,
        profile.executor, 
        profile.accounting, 
        profile.portfolio_factory,
        warmup_bars=profile.warmup_bars,
        hold_last_fold=True,
        observers=[recorder],
        handoff = profile.handoff
    )

    save_schedule_replay(
        run_dir, 
        schedule=extension.schedule, 
        oos_replay=replay, 
        trace=recorder.frame(),
        specs=inputs.specs,
        manifest={"profile": name, "kind": "schedule_replay", "new_folds": len(extension.new_selected_folds)},
        overwrite=True
    )
    decision = profile.decision_series(context, schedule=extension.schedule) if profile.decision_series else None
    
    return render_run(run_dir, decision=decision)