from __future__ import annotations

from typing import Any, Mapping

from pystrat.context.context_data import Context
from pystrat.domain.portfolio.accounting.accounting_futures import FuturesAccounting
from pystrat.domain.portfolio.portfolio_data import Portfolio
from pystrat.execution.executors.immediate_executor import ImmediateExecutor
from pystrat.features.features_services import zscore
from pystrat.research.calibration.walk_forward.search_scores import mean_segment_search_score
from pystrat.research.objective.objective_data import ObjectiveConfig
from pystrat.research.optimizer.optimizers.optuna_optimizer import OptunaOptimizer
from pystrat.research.optimizer.optimizers.grid_optimizer import GridOptimizer
from pystrat.research.optimizer.optimizers.optuna_optimizer import OptunaOptimizer
from pystrat.research.optimizer.optimizers.random_optimizer import RandomOptimizer

from pystrat.research.search_space.search_params.choice_param import Choice
from pystrat.research.selection.selectors.robust_selector import RobustSelector
from pystrat.research.selection.selectors.temporal_robust_selector import TemporalRobustSelector
from pystrat.research.split.splitters.walk_forward_splitter import WalkForwardSplitter
from pystrat.signals.generators.transform_generator import TransformGenerator
from pystrat.strategy.core.strategy_protocol import Strategy
from pystrat.strategy.core.targets.targets_data import TargetUnit
from pystrat.strategy.deciders.armed_tiered_decider import ArmedTieredDecider
from pystrat.strategy.strategies.pipeline_strategy import PipelineStrategy
from pystrat.strategy.strategies.piecewise_strategy import Handoff

from market_intel_pystrat.data.profile_inputs_data import CORN_KEY, SPOT_ARG_COLUMN
from market_intel_pystrat.profiles.profile_data import MarketIntelProfile

# Legacy profile_corn_arg: load window, tiered sizing and capital.
DATA_START = "2021-12-01"
DATA_END = "2026-07-01"
_BASE_NOTIONAL = 300_000_000.0
_CAPITAL = 300_000_000.0
_TIERS = ((1.0, _BASE_NOTIONAL * 1.00), (2.0, _BASE_NOTIONAL * 1.50))
# _TIERS = ((1.0, _BASE_NOTIONAL * 0.8), (2.0, _BASE_NOTIONAL * 1.2))



# Covers the max feature lookback (diff.periods 9 + zscore.window 100).
_WARMUP_BARS = 110


def add_features(context: Context) -> Context:
    """No shared feature: the searched (diff, zscore) pipeline lives in the strategy."""
    return context


# def make_space() -> dict:
#     """Legacy optuna space: diff.periods in {1,3,5,7,9}, zscore.window in {5..100 step 5}."""
#     return {
#         "periods": Choice(tuple(range(1, 10, 2))),
#         "window": Choice(tuple(range(5, 101, 5))),
#     }
def make_space() -> dict:
    """Legacy optuna space: diff.periods in {1,3,5,7,9}, zscore.window in {5..100 step 5}."""
    return {
        "periods": Choice(tuple(range(1, 11, 3))),

        "window": Choice(tuple(range(10, 101, 10))),
    }

def build_strategy(params: Mapping[str, Any]) -> Strategy:
    """Arm-and-confirm on zscore(diff(ARG spot mid)), tiered fixed-notional CORN target."""
    periods = int(params["periods"])
    window = int(params["window"])
    return PipelineStrategy(
        generators=[
            TransformGenerator(
                instrument_key=CORN_KEY,
                feature=SPOT_ARG_COLUMN,
                transform=lambda s: zscore(s.diff(periods), window),
                # transform=lambda s: zscore(
                #     s.resample("D").ffill().diff(periods), window
                # ).reindex(s.index)
            )
        ],
        decider=ArmedTieredDecider(tiers=_TIERS, unit=TargetUnit.NOTIONAL_AT_ENTRY),
    )

import pandas as pd
def decision_series(context: Context, schedule: Mapping[str, Any]) -> Mapping[str, Any]:

    spot = context.frames[CORN_KEY][SPOT_ARG_COLUMN]
    stitched = pd.Series(float("nan"), index=spot.index, name="zscore")
    for key in sorted(schedule, key=int):
        entry = schedule[key]
        params = entry["best_params"]
        z = zscore(spot.diff(int(params["periods"])), int(params["window"]))
        i0, i1 = int(entry["test_start_idx"]), int(entry["test_end_idx_exclusive"])
        stitched.iloc[i0:i1] = z.iloc[i0:i1]
    out = {"zscore": stitched}
    for level, _ in _TIERS:
        out[f"+{level:g}"] = pd.Series(float(level), index=spot.index)
        out[f"-{level:g}"] = pd.Series(float(-level), index=spot.index)
    return out


def score_corn_arg(metrics: Mapping[str, float]) -> float:
    """Legacy objective: sharpe only."""
    return float(metrics["calmar"])


def profile() -> MarketIntelProfile:
    """Replication of legacy profile_corn_arg (zscore of diffed ARG spot)."""
    return MarketIntelProfile(
        name="corn_arg_zscore",
        add_features=add_features,
        optimizer=OptunaOptimizer.from_search_space(make_space(), n_trials=15, seed=42), # best is 15
        # optimizer=RandomOptimizer(make_space(), n_trials=20, seed=42),
        # optimizer=GridOptimizer(make_space()),

        search_score=mean_segment_search_score("train"),
        build_strategy=build_strategy,
        objective=ObjectiveConfig(score_corn_arg),
        splitter=WalkForwardSplitter(
            train_bars=63, test_bars=21, step_bars=21, validation_bars=21
        ),
        selector=TemporalRobustSelector(slices = (("train", 3), ("validation", 2)),
                                        slice_score = score_corn_arg),        
        accounting=FuturesAccounting(),
        executor=ImmediateExecutor(),
        portfolio_factory=lambda: Portfolio(cash=_CAPITAL),
        key=CORN_KEY,
        warmup_bars=_WARMUP_BARS,
        per_fold_search = True,
        decision_series=decision_series,
        handoff = Handoff.HOLD

    )