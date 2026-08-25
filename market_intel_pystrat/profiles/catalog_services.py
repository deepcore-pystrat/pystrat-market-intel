from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from market_intel_pystrat.data.profile_inputs_data import ProfileInputs
from market_intel_pystrat.profiles.catalog_data import ProfileEntry

SOURCES = ("excel", "postgres")


def load_profile_inputs(
    entry: ProfileEntry,
    source: str = "excel",
    data_dir: Optional[Union[str, Path]] = None,
) -> ProfileInputs:
    """Load a profile's inputs from 'excel' (requires data_dir) or 'postgres'."""
    if source == "excel":

        if data_dir is None:
            raise ValueError(
                "source 'excel' requires data_dir (set MARKET_INTEL_DATA_DIR)"
            )
        
        return entry.load_inputs_excel(data_dir)
    
    if source == "postgres":

        if entry.load_inputs_postgres is None:
            raise ValueError("this profile has no postgres loader")
        
        return entry.load_inputs_postgres()
    
    raise ValueError(f"unknown source '{source}'. Available: {SOURCES}")