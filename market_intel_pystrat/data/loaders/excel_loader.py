from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Union, Optional

from pystrat.data_source.providers.excel_provider import ExcelProvider, ExcelSource
from pystrat.data_source.readers.ohlcv_readers import read_ohlcv
from pystrat.data_source.readers.basis_readers import read_basis_mono, read_basis_multi
from pystrat.data_source.readers.regime_readers import read_regime_csv
from market_intel_pystrat.data.loaders.excel_catalog_data import REGIME_FILES
from market_intel_pystrat.data.profile_inputs_data import (
    BASIS_THP_KEY,
    BASIS_VHP_KEY,
    ProfileInputs,
    SB11_KEY,
    CORN_KEY,
    BASIS_CORN_ARG_KEY,
    BASIS_CORN_BRZ_KEY,
)
from market_intel_pystrat.data.loaders.excel_catalog_data import (
    BASIS_MONO_FILES,
    COFFEE_BASIS_FILE,
    COFFEE_BASIS_SHEETS,
    FUTURES_FILES,
)
from market_intel_pystrat.data.assembly.sb11_assembly_services import assemble_sb11_basis_inputs
from market_intel_pystrat.data.assembly.corn_assembly_services import assemble_corn_inputs



def build_excel_provider(data_dir: Union[str, Path]) -> ExcelProvider:
    """ExcelProvider over every catalog file in `data_dir` (see excel_catalog_data)."""
    data_dir = Path(data_dir)
    sources = {}
    for key, file_name in FUTURES_FILES.items():
        sources[key] = ExcelSource(path=data_dir / file_name, reader=read_ohlcv)
    for key, file_name in BASIS_MONO_FILES.items():
        sources[key] = ExcelSource(path=data_dir / file_name, reader=read_basis_mono)
    for key, sheet in COFFEE_BASIS_SHEETS.items():
        sources[key] = ExcelSource(
            path=data_dir / COFFEE_BASIS_FILE,
            reader=partial(read_basis_multi, sheet_name=sheet),
        )

    for key, file_name in REGIME_FILES.items():
        sources[key] = ExcelSource(path=data_dir / file_name, reader=read_regime_csv)
    return ExcelProvider(sources=sources)


def load_sb11_basis_inputs(
    data_dir: Union[str, Path],
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> ProfileInputs:
    """SB11 ProfileInputs from the Excel files in `data_dir`."""
    provider = build_excel_provider(data_dir)
    return assemble_sb11_basis_inputs(
        ohlcv=provider.get_data(SB11_KEY),
        vhp=provider.get_data(BASIS_VHP_KEY),
        thp=provider.get_data(BASIS_THP_KEY),
        start=start,
        end=end,
    )

def load_corn_inputs(
    data_dir: Union[str, Path],
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> ProfileInputs:
    """Corn ProfileInputs from the Excel files in `data_dir`."""
    provider = build_excel_provider(data_dir)
    return assemble_corn_inputs(
        ohlcv=provider.get_data(CORN_KEY),
        arg=provider.get_data(BASIS_CORN_ARG_KEY),
        brz=provider.get_data(BASIS_CORN_BRZ_KEY),
        regimes=provider.get_data("HMM_CORN"), 
        start=start,
        end=end,
    )