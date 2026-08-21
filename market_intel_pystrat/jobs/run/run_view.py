from __future__ import annotations

from pathlib import Path
from typing import Union

from market_intel_pystrat.jobs.report import render_run


def run_view(run_dir: Union[str, Path]) -> Path:
    return render_run(run_dir)