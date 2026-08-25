from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence, Optional

import pandas as pd

from pystrat.context.context_data import Context
from pystrat.domain.portfolio.accounting.accounting_protocol import AccountingModel
from pystrat.domain.portfolio.portfolio_data import Portfolio
from pystrat.execution.execution_protocol import ExecutionModel
from pystrat.research.objective.objective_data import ObjectiveConfig
from pystrat.research.selection.selector_protocol import Selector
from pystrat.research.split.splitter_protocol import Splitter
from pystrat.strategy.core.strategy_protocol import Strategy
from pystrat.research.calibration.preparer.preparer_protocol import CandidatePreparer
from pystrat.research.optimizer.optimizer_protocol import Optimizer
from pystrat.research.optimizer.optimizer_data import CandidateEvaluation
from pystrat.research.calibration.walk_forward.segment_data import CandidateReport
from pystrat.strategy.strategies.piecewise_strategy import Handoff

@dataclass(frozen=True)
class MarketIntelProfile:
    """Complete declaration of one strategy study: everything the jobs need to
    calibrate, replay, extend and report it (data enters separately via ProfileInputs)."""

    name : str
    add_features : Callable[[Context], Context]
    build_strategy : Callable[[Mapping[str, Any]], Strategy]
    objective : ObjectiveConfig
    splitter : Splitter
    selector : Selector
    accounting : AccountingModel
    executor : ExecutionModel
    portfolio_factory : Callable[[], Portfolio]
    optimizer : Optimizer
    search_score : Callable[[CandidateReport], CandidateEvaluation]

    key : str = "SB11"
    warmup_bars : int = 0
    preparer : Optional[CandidatePreparer] = None
    per_fold_search : bool = False
    decision_series : Optional[Callable[[Context, Mapping[str, Any]], Mapping[str, pd.Series]]] = None
    handoff : Handoff = Handoff.RESCAN
    
    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("MarketIntelProfile name must be non-empty")
        if self.warmup_bars < 0:
            raise ValueError("MarketIntelProfile warmup_bars must be >= 0")        