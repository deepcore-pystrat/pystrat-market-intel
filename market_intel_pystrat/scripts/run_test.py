import os
from pathlib import Path

import pandas as pd

from market_intel_pystrat.data.loaders.excel_loader import build_excel_provider
from market_intel_pystrat.data.loaders.postgres_loader import build_postgres_provider

pd.set_option("display.width", 200)

xl = build_excel_provider(Path(os.environ["MARKET_INTEL_DATA_DIR"]))
pg = build_postgres_provider()


def _diff_series(label: str, a: pd.Series, b: pd.Series) -> None:
    common = a.index.intersection(b.index)
    mask = (a.loc[common] - b.loc[common]).abs() > 1e-9
    print(
        f"[{label}] communes={len(common)} | XL only={len(a.index.difference(b.index))} "
        f"| PG only={len(b.index.difference(a.index))} | diffs={mask.sum()}"
        + (f" | max abs={(a.loc[common] - b.loc[common]).abs().max():.4f}" if mask.any() else "")
    )


# --- corn spots: bid/offer mono-series ---
for key in ["BASIS_CORN_ARG", "BASIS_CORN_BRZ"]:
    fx, fp = xl.get_data(key), pg.get_data(key)
    for col in ["bid", "offer"]:
        _diff_series(f"{key}.{col}", fx[col], fp[col])

# --- coffee spots: long form -> pivot value par origine ---
for key in ["BASIS_COFFEE_ARBC", "BASIS_COFFEE_RBST"]:
    fx, fp = xl.get_data(key), pg.get_data(key)
    px = fx.pivot_table(index=fx.index, columns="origin", values="value")
    pp = fp.pivot_table(index=fp.index, columns="origin", values="value")
    print(f"\n===== {key}: origines XL={sorted(px.columns)} | PG={sorted(pp.columns)}")
    for origin in px.columns.intersection(pp.columns):
        _diff_series(f"{key}.{origin}", px[origin].dropna(), pp[origin].dropna())