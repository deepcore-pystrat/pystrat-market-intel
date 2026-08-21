from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional, Union

import pandas as pd

from pystrat.plotting.diagnostic_plots import plot_strategy_diagnostic
from pystrat.plotting.wf_plots import (
    plot_equity_vs_buyhold_frame,
    plot_oos_drawdown_frame,
    plot_oos_equity_frame,
    plot_selection_by_fold_frame,
)
from pystrat.research.artifacts.artifacts_services import load_run

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pystrat.research.artifacts.artifacts_services import load_schedule_replay
_DECISION_FILE = "decision_series.csv"


def _html_document(title, figures) -> str:
    parts = [f.to_html(full_html=False, include_plotlyjs=("cdn" if i == 0 else False))
             for i, f in enumerate(figures)]
    return (f"<html><head><meta charset='utf-8'><title>{title}</title></head>"
            f"<body><h1>{title}</h1>" + "".join(parts) + "</body></html>")


def _write_decision_series(run_dir: Path, decision: Mapping[str, pd.Series]) -> None:
    index = next(iter(decision.values())).index
    df = pd.DataFrame({name: pd.Series(s).to_numpy() for name, s in decision.items()})
    df.insert(0, "date", index)
    df.to_csv(run_dir / _DECISION_FILE, index=False)


def _read_decision_series(run_dir: Path) -> Mapping[str, pd.Series]:
    f = run_dir / _DECISION_FILE
    if not f.exists():
        return {}
    df = pd.read_csv(f)
    if "date" not in df.columns:
        return {}
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.set_index("date")
    return {c: df[c] for c in df.columns}


def _manifest_kind(run_dir: Path) -> str:
    f = run_dir / "manifest.json"
    return json.loads(f.read_text()).get("kind", "calibration") if f.exists() else "calibration"


def _schedule_folds_frame(schedule) -> pd.DataFrame:
    rows = []
    for key in sorted(schedule, key=int):
        e = schedule[key]
        row = {"fold": int(key) - 1, "test_start_ts": pd.Timestamp(e["test_start"])}
        row.update({f"param_{k}": v for k, v in e["best_params"].items()})
        rows.append(row)
    return pd.DataFrame(rows)


def _threshold_step_series(schedule, index):
    lows = pd.Series(index=index, dtype=float)
    highs = pd.Series(index=index, dtype=float)
    for key in sorted(schedule, key=int):
        ts = pd.Timestamp(schedule[key]["test_start"])
        p = schedule[key]["best_params"]
        lows.loc[lows.index >= ts] = p["low"]
        highs.loc[highs.index >= ts] = p["high"]
    return lows, highs



def save_report_html(run_dir: Path, *, title: str = "Calibration report") -> Path:
    b = load_run(run_dir)
    param_cols = [c for c in b.selected_folds.columns if c.startswith("param_")]
    figs = [plot_oos_equity_frame(b.oos_equity, b.oos_fills, b.selected_folds, param_cols=param_cols),
            plot_oos_drawdown_frame(b.oos_equity),
            plot_selection_by_fold_frame(b.selected_folds, param_cols=param_cols)]
    out = run_dir / "report.html"
    out.write_text(_html_document(title, figs), encoding="utf-8")
    return out


def save_view_html(run_dir: Path, *, title: str = "Schedule replay view") -> Path:
    b = load_run(run_dir)
    folds_df = _schedule_folds_frame(b.calibration_schedule)
    param_cols = [c for c in folds_df.columns if c.startswith("param_")]
    figs = [plot_oos_equity_frame(b.oos_equity, b.oos_fills, folds_df, param_cols=param_cols),
            plot_oos_drawdown_frame(b.oos_equity)]
    out = run_dir / "view.html"
    out.write_text(_html_document(title, figs), encoding="utf-8")
    return out


def save_diagnostic_html(run_dir: Path, *, title: str = "Strategy diagnostic") -> Path:
    b = load_run(run_dir)
    trace, fills, schedule = b.oos_trace, b.oos_fills, b.calibration_schedule
    price = trace.set_index("timestamp")["price"] if not trace.empty else pd.Series(dtype=float)
    decision = dict(_read_decision_series(run_dir))
    decision = dict(_read_decision_series(run_dir))
    has_thresholds = bool(schedule) and all(
        "low" in e["best_params"] and "high" in e["best_params"] for e in schedule.values()
    )
    if not price.empty and has_thresholds:
        decision["low"], decision["high"] = _threshold_step_series(schedule, price.index)
    diag = plot_strategy_diagnostic(price, trace, fills, decision_series=decision,
                                    folds=_schedule_folds_frame(schedule),
                                    title="Price / decider / position")
    bh = plot_equity_vs_buyhold_frame(b.oos_equity, price, title="Strategy vs buy & hold")
    out = run_dir / "diagnostic.html"
    out.write_text(_html_document(title, [diag, bh]), encoding="utf-8")
    return out


def _normalized(series: pd.Series) -> pd.Series:
    return series / series.iloc[0]


def _exposure_summary_table(target: pd.Series, qty: pd.Series) -> go.Figure:
    exposed = qty != 0.0
    rows = [
        ("bars", f"{len(qty)}"),
        ("exposed", f"{exposed.mean():.1%}"),
        ("long", f"{(qty > 0).mean():.1%}"),
        ("short", f"{(qty < 0).mean():.1%}"),
        ("avg |notional target| when exposed",
         f"{target[exposed].abs().mean():,.0f}" if exposed.any() else "-"),
        ("max |notional target|", f"{target.abs().max():,.0f}"),
    ]
    fig = go.Figure(go.Table(header=dict(values=["exposure", "value"]),
                             cells=dict(values=[[r[0] for r in rows],
                                                [r[1] for r in rows]])))
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
    return fig


def save_fusion_diagnostic_html(run_dir: Path, *, title: str = "Fusion diagnostic") -> Path:
    b = load_schedule_replay(run_dir)
    components = b.manifest.get("components", [])
    eq = b.oos_equity.set_index("date")["equity"]
    start, end = eq.index[0], eq.index[-1]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
        vertical_spacing=0.06, specs=[[{}], [{"secondary_y": True}]],
        subplot_titles=("Normalized equity: fusion vs components vs buy & hold",
                        "Exposure: fused notional target / contracts"))

    fig.add_trace(go.Scatter(x=eq.index, y=_normalized(eq), name="fusion",
                             line=dict(width=3)), row=1, col=1)

    for name in components:
        f = run_dir.parent / name / "oos_equity.csv"
        if not f.exists():
            continue
        ce = pd.read_csv(f)
        ce["date"] = pd.to_datetime(ce["date"], utc=True)
        ce = ce.set_index("date")["equity"].loc[start:end]
        if len(ce) >= 2:
            fig.add_trace(go.Scatter(x=ce.index, y=_normalized(ce), name=name,
                                     line=dict(width=1.2)), row=1, col=1)

    # figs = [fig]
    figs = []

    if not b.oos_trace.empty:
        t = b.oos_trace.sort_values("timestamp")
        price = t.groupby("timestamp")["price"].first().loc[start:end]
        target = t.groupby("timestamp")["target_value"].first().fillna(0.0)
        qty = t.groupby("timestamp")["position_quantity"].first()

        fig.add_trace(go.Scatter(x=price.index, y=_normalized(price), name="buy & hold",
                                 line=dict(dash="dot", color="grey")), row=1, col=1)
        fig.add_trace(go.Scatter(x=target.index, y=target, name="notional target",
                                 line_shape="hv", fill="tozeroy"), row=2, col=1)
        fig.add_trace(go.Scatter(x=qty.index, y=qty, name="contracts",
                                 line_shape="hv", line=dict(color="black", width=1)),
                      row=2, col=1, secondary_y=True)
        # figs.append(_exposure_summary_table(target, qty))

    fig.update_layout(height=800, hovermode="x unified")

    # if not b.oos_trace.empty:
    #     price_full = b.oos_trace.set_index("timestamp")["price"]
    #     figs.insert(0, plot_strategy_diagnostic(
    #         price_full, b.oos_trace, b.oos_fills,
    #         title="Fusion: price / fills / position"))

    if not b.oos_trace.empty:
        price_full = b.oos_trace.set_index("timestamp")["price"]
        figs.insert(0, plot_strategy_diagnostic(
            price_full, b.oos_trace, b.oos_fills,
            title="Fusion: price / fills / position"))
        figs.insert(1, plot_equity_vs_buyhold_frame(
            b.oos_equity, price_full, title="Fusion vs buy & hold"))

        
    out = run_dir / "diagnostic.html"
    out.write_text(_html_document(title, figs), encoding="utf-8")
    return out
















_RENDERERS = {
    "calibration":     (save_report_html, save_diagnostic_html),
    "schedule_replay": (save_view_html,   save_diagnostic_html),
    "fusion":          (save_fusion_diagnostic_html,),
}


def render_run(run_dir: Union[str, Path], decision: Optional[Mapping[str, pd.Series]] = None) -> Path:
    run_dir = Path(run_dir)
    if decision:
        _write_decision_series(run_dir, decision)
    for renderer in _RENDERERS[_manifest_kind(run_dir)]:
        renderer(run_dir)
    return run_dir