from __future__ import annotations

from typing import Any, List, Mapping

from pystrat.context.context_data import Context
from pystrat.domain.portfolio.accounting.accounting_futures import FuturesAccounting
from pystrat.domain.portfolio.portfolio_data import Portfolio
from pystrat.execution.executors.immediate_executor import ImmediateExecutor
from pystrat.features.features_services import rsi_ewm_smooth
from pystrat.research.objective.objective_data import ObjectiveConfig

from pystrat.research.selection.selectors.best_train_selector import BestTrainSelector
from pystrat.research.selection.selectors.robust_selector import RobustSelector
from pystrat.research.selection.selectors.temporal_robust_selector import TemporalRobustSelector


from pystrat.research.search_space.search_params.choice_param import Choice

from pystrat.research.optimizer.optimizers.grid_optimizer import GridOptimizer
from pystrat.research.optimizer.optimizers.optuna_optimizer import OptunaOptimizer
from pystrat.research.optimizer.optimizers.random_optimizer import RandomOptimizer

from pystrat.research.calibration.walk_forward.search_scores import mean_segment_search_score

from pystrat.research.split.splitters.walk_forward_splitter import WalkForwardSplitter
from pystrat.signals.generators.id_generator import IdentityGenerator
from pystrat.strategy.core.strategy_protocol import Strategy
from pystrat.strategy.core.targets.targets_data import TargetUnit
from pystrat.strategy.deciders.crossings import CrossMode
from pystrat.strategy.deciders.threshold_cross_decider import ThresholdCrossDecider
from pystrat.strategy.strategies.pipeline_strategy import PipelineStrategy
from pystrat.strategy.strategies.piecewise_strategy import Handoff

from market_intel_pystrat.data.profile_inputs_data import (
    BASIS_THP_COLUMN,
    BASIS_VHP_COLUMN,
    SB11_KEY,
    FUTURE_CLOSE_COLUMN,
)
from market_intel_pystrat.profiles.profile_data import MarketIntelProfile

SIGNAL_COLUMN = "spread_rsi"

DATA_START = None
DATA_END = "2024-01-01"
# Legacy wf_sb11 fixed feature hyperparameters, sizing and capital.
_RSI_WINDOW = 15
_SMOOTH_SPAN = 2
_NOTIONAL_USD = 300_000_000.0
_CAPITAL = 300_000_000.0

_WARMUP_BARS = 0


# Legacy active threshold grid: low in {-0.5..-2.5}, high in {0.5..2.5}.
_LOWS = [i for i in range(10, 41, 5)] # cétait step=10 à la base avec n_trials=20/30
_HIGHS = [i for i in range(60, 91, 5)]


from pystrat.data_source.core import schema

def add_features(context: Context) -> Context:
    frames = dict(context.frames)
    frame = frames[SB11_KEY]

    close = frame[FUTURE_CLOSE_COLUMN].shift(1)
    signal = rsi_ewm_smooth(close, window=_RSI_WINDOW, smooth_span=_SMOOTH_SPAN)

    frames[SB11_KEY] = frame.assign(**{SIGNAL_COLUMN: signal})
    return Context(clock=context.clock, frames=frames)


def make_space() -> dict:
    """Same (low, high) grid as make_candidates(), as a SearchSpace."""
    return {"low": Choice(tuple(_LOWS)), "high": Choice(tuple(_HIGHS))}

def build_strategy(params: Mapping[str, Any]) -> Strategy:
    """Reversion cross on the RSI, fixed-notional SB11 target."""
    return PipelineStrategy(
        generators=[IdentityGenerator(instrument_key=SB11_KEY, feature=SIGNAL_COLUMN)],
        decider=ThresholdCrossDecider(
            high=params["high"],
            low=params["low"],
            size=_NOTIONAL_USD,
            unit=TargetUnit.NOTIONAL_AT_ENTRY,
            direction=1,
            mode=CrossMode.IN,
        ),
    )

def decision_series(context: Context, schedule : Mapping[str, Any]) -> Mapping[str, Any]:
    """Panel-2 series for the diagnostic: the causal RSI of the spread."""
    return {"rsi": context.frames[SB11_KEY][SIGNAL_COLUMN]}


def score_wf_sb11(metrics: Mapping[str, float]) -> float:
    """Legacy objective for wf_sb11: sharpe + 10*mdd (mdd < 0 penalises DD)."""
    # return float(metrics["sharpe"]) + 10.0 * float(metrics["mdd"])
    return float(metrics["calmar"])


def profile() -> MarketIntelProfile:
    """Assemble the wf_sb11 replication profile."""
    return MarketIntelProfile(
        name="sb11_rsi_fut",
        add_features=add_features,
        
        # optimizer=GridOptimizer(make_space()),
        # optimizer=RandomOptimizer(make_space(), n_trials=20, seed=42),
        optimizer=OptunaOptimizer.from_search_space(make_space(), n_trials=5, seed=42),
        
        search_score=mean_segment_search_score("train"),
        build_strategy=build_strategy,
        objective=ObjectiveConfig(score_wf_sb11),
        # splitter=WalkForwardSplitter(train_bars=168, test_bars=42, step_bars=42),
        splitter=WalkForwardSplitter(
            train_bars=63, test_bars=21, step_bars=21, validation_bars=21
        ),
        # splitter=WalkForwardSplitter(
        #     train_bars=126, test_bars=42, step_bars=42, validation_bars=42
        # ),

        # selector=BestTrainSelector(),
        # selector=RobustSelector(2),
        selector=TemporalRobustSelector(slices = (("train", 3), ("validation", 2)),
                                        slice_score = score_wf_sb11),
        accounting=FuturesAccounting(),
        executor=ImmediateExecutor(),
        portfolio_factory=lambda: Portfolio(cash=_CAPITAL),
        key=SB11_KEY,
        warmup_bars=_WARMUP_BARS,
        per_fold_search = True,
        decision_series=decision_series,
        handoff = Handoff.HOLD
        # handoff = Handoff.RESCAN
    )



