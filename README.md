# pystrat-market-intel

Market Intel (DeepCore) strategy profiles built on top of the [pystrat](https://github.com/deepcore-pystrat/pystrat-lib) backtesting library: data loading, walk-forward calibration, out-of-sample replay and HTML reporting for the commodity models (sugar, corn).

## Installation

Requires Python >= 3.9 and access to the `deepcore-pystrat` GitHub organization (the `pystrat` library is installed from GitHub automatically).

```bash
git clone https://github.com/deepcore-pystrat/pystrat-market-intel.git
cd pystrat-market-intel
python -m venv .venv
.venv\Scripts\activate        # Windows (Linux/macOS: source .venv/bin/activate)
pip install -e .[dev,postgres]
```

`[postgres]` is only needed to read the DeepCore database; `[dev]` adds pytest.

## Data sources

Every profile can load its inputs from one of two sources:

### Excel (`--source excel`, default)
Set the environment variable `MARKET_INTEL_DATA_DIR` to the folder containing the data files (`data_futures_sb11.xlsx`, `data_spot_VHP.xlsx`, ...). These files are **not** in the repo — ask the team for a copy.

```powershell
$env:MARKET_INTEL_DATA_DIR = "C:\path\to\data"
```

### Postgres (`--source postgres`)
Copy `.env.example` to `.env` at the repo root and fill in your DeepCore DB credentials (never commit `.env`). Environment variables work too.

Currently available in the DB: SB11 futures, VHP/THP/CORN_ARG/CORN_BRZ spots, coffee spots. **CORN futures are not populated yet**, so the corn profiles are Excel-only for now.

## Usage

```bash
# Full calibration of a profile (writes artifacts/runs/<profile>/)
python -m market_intel_pystrat.scripts.run calibration corn_brz_zscore

# Extend an existing run with newly available data, replay and re-render
python -m market_intel_pystrat.scripts.run update sb11_zscore --source postgres

# Re-render the HTML reports of a saved run (no computation)
python -m market_intel_pystrat.scripts.run view corn_brz_zscore

# Replay several calibrated components under a fused strategy
python -m market_intel_pystrat.scripts.run fusion corn_fusion_majority
```

Profiles and fusions are declared in `market_intel_pystrat/profiles/catalog_data.py` (`REGISTRY` / `FUSIONS`).

## Run artifacts

Each run directory (`artifacts/runs/<name>/`) contains the replayable core: `calibration_schedule.json` (per-fold chosen params), OOS equity/fills/trades/trace CSVs, `oos_metrics.json`, a `manifest.json`, and the HTML reports (`report.html`, `view.html`, `diagnostic.html`).

## Adding a new profile

1. Create the profile module (see `profiles/corn_profiles/` for examples): `make_space`, `build_strategy`, objective score, `profile()`
2. If it needs new data, add an assembly in `data/assembly/` and loaders in `data/loaders/`
3. Register it in `REGISTRY` in `profiles/catalog_data.py`

## Tests

```bash
python -m pytest -q
```
