from __future__ import annotations

from pathlib import Path
from typing import Union

from pystrat.context.context_data import Context
from pystrat.engine.recorders import BarTraceRecorder
from pystrat.research.artifacts.artifacts_services import save_run
from pystrat.research.calibration.walk_forward.walk_forward_services import evaluate_candidates
from pystrat.research.calibration.replay.replay_services import replay_oos
from pystrat.research.selection.selection_services import select_per_fold

from market_intel_pystrat.data.profile_inputs_data import ProfileInputs
from market_intel_pystrat.profiles.profile_data import MarketIntelProfile
from pystrat.research.calibration.walk_forward.walk_forward_services import (
    run_walk_forward,
    run_walk_forward_per_fold,
)
def calibrate(profile: MarketIntelProfile, inputs: ProfileInputs,
              out_dir: Union[str, Path], *, overwrite: bool = False) -> Context:
    """Full calibration of one profile: search, per-fold selection, OOS replay, artifacts.

    Returns the feature-enriched Context so callers can derive decision series.
    """
    context = profile.add_features(inputs.context)

    search = run_walk_forward_per_fold if profile.per_fold_search else run_walk_forward
    result = search(
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
        preparer=profile.preparer,
        warmup_bars=profile.warmup_bars,
    )
    selected = select_per_fold(result.reports, profile.selector)

    recorder = BarTraceRecorder()
    oos = replay_oos(
        selected, 
        profile.build_strategy, 
        context, 
        inputs.price_frames, 
        inputs.specs,
        profile.executor, 
        profile.accounting, 
        profile.portfolio_factory,
        warmup_bars=profile.warmup_bars, 
        observers=[recorder],
        handoff=profile.handoff,
    )

    save_run(
        out_dir, 
        reports=result.reports,
        selected=selected, 
        oos_replay=oos,
        clock_index=context.clock.index, 
        trace=recorder.frame(),
        specs=inputs.specs,
        manifest={"profile": profile.name, "kind": "calibration"},
        overwrite=overwrite
        )
    
    return context