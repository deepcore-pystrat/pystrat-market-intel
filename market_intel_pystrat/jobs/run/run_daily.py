from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Sequence, Union

from market_intel_pystrat.data.ibkr.ibkr_services import fetch_and_upsert
from market_intel_pystrat.jobs.run.run_update import run_update

# Profiles refreshed by the daily job. Corn profiles: add them once the CORN
# futures history is backfilled in the DB.
FOLLOWED_PROFILES = ("sb11_zscore", "sb11_rsi", "sb11_rsi_fut")


def run_daily(
    runs_root: Union[str, Path] = Path("artifacts/runs"),
    *,
    profiles: Sequence[str] = FOLLOWED_PROFILES,
    source: str = "postgres",
    ingest: bool = True,
    duration: str = "2 D",
    data_dir: Optional[Union[str, Path]] = None,
) -> Dict:
    """Daily automation: ingest the latest IBKR bars, then update every followed profile.

    Failures are isolated: an ingestion failure skips the updates (data would
    be unchanged); a failing profile does not stop the others. Returns a
    report dict: {"ingestion": ..., "profiles": {name: "ok" | "error: ..."}}.
    """
    report: Dict = {"ingestion": "skipped", "profiles": {}}
    runs_root = Path(runs_root)

    if ingest:
        try:
            counts = fetch_and_upsert(duration=duration)
            report["ingestion"] = {
                asset: f"{ins} inserted, {upd} updated" for asset, (ins, upd) in counts.items()
            }
        except Exception as exc:
            report["ingestion"] = f"error: {exc}"
            report["profiles"] = {name: "skipped (ingestion failed)" for name in profiles}
            return report

    for name in profiles:
        try:
            run_update(name, runs_root / name, data_dir, source=source)
            report["profiles"][name] = "ok"
        except Exception as exc:
            report["profiles"][name] = f"error: {exc}"

    return report


def has_failures(report: Dict) -> bool:
    """True if the ingestion errored or any profile did not update cleanly."""
    ingestion = report["ingestion"]
    if isinstance(ingestion, str) and ingestion.startswith("error"):
        return True
    return any(status != "ok" for status in report["profiles"].values())
