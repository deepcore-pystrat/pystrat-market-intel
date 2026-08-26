# pystrat-market-intel

Market Intel (DeepCore) strategy profiles built on top of the [pystrat](https://github.com/deepcore-pystrat/pystrat-lib) backtesting library: data loading, walk-forward calibration, out-of-sample replay and HTML reporting for the commodity models (sugar, corn).

## Installation

Requires Python >= 3.9 and access to the `deepcore-pystrat` GitHub organization. `pystrat` is a separate **library** repo ([pystrat-lib](https://github.com/deepcore-pystrat/pystrat-lib)); this repo is the **application** that depends on it, the same way it depends on pandas. Pick the scenario that matches your role.

### Scenario A — use / develop this project only (most common)

You do **not** need to clone the library: pip fetches it from GitHub automatically (you will be asked to authenticate, since the repo is private).

```bash
git clone https://github.com/deepcore-pystrat/pystrat-market-intel.git
cd pystrat-market-intel
python -m venv .venv
.venv\Scripts\activate        # Windows (Linux/macOS: source .venv/bin/activate)
python -m pip install --upgrade pip   # stock pip 21.x cannot do modern editable installs
pip install -e .[dev,postgres]
```

`[postgres]` is only needed to read the DeepCore database; `[dev]` adds pytest.

> ⚠️ In this scenario the installed `pystrat` is a **frozen copy** taken at install time.
> When new library changes are pushed, `git pull` on this repo is NOT enough — you must
> reinstall the library:
>
> ```bash
> pip install --force-reinstall --no-deps "pystrat @ git+https://github.com/deepcore-pystrat/pystrat-lib.git"
> ```
>
> Classic symptom of forgetting this: "I pulled but it still doesn't work."

### Scenario B — also contribute to the pystrat library

Clone **both** repos side by side and install the library in editable mode, so `import pystrat` points at your local clone and every edit is picked up immediately:

```bash
git clone https://github.com/deepcore-pystrat/pystrat-lib.git
git clone https://github.com/deepcore-pystrat/pystrat-market-intel.git

cd pystrat-market-intel
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip

pip install -e .[dev,postgres]         # the project first (pulls a frozen pystrat from GitHub)
pip install -e ../pystrat-lib          # the library LAST: the editable clone overrides the frozen copy
```

### Day-to-day team workflow

```bash
git pull                    # in every repo you cloned, to get others' work
# ... work, then:
git add .
git commit -m "..."
git push
```

Rules of thumb:
- A library change can break this project: after pulling `pystrat-lib`, run `python -m pytest -q` in **both** repos
- Scenario A + library updated upstream = reinstall pystrat (see warning above)
- Never commit `.env` or real credentials; `artifacts/runs/` contains the shared reference runs — do not overwrite them casually

## Data sources

Every profile can load its inputs from one of two sources:

### Excel (`--source excel`, default)
Set the environment variable `MARKET_INTEL_DATA_DIR` to the folder containing the data files (`data_futures_sb11.xlsx`, `data_spot_VHP.xlsx`, ...). These files are **not** in the repo — ask the team for a copy.

```powershell
$env:MARKET_INTEL_DATA_DIR = "C:\path\to\data"
```

### Postgres (`--source postgres`)
Copy `.env.example` to `.env` at the repo root and fill in your DeepCore DB credentials (never commit `.env`). Environment variables work too.

Currently available in the DB: SB11 futures, VHP/THP/CORN_ARG/CORN_BRZ spots, coffee spots. **CORN futures are not populated yet**: the corn profiles are fully wired for postgres (loader + registry) but only work with `--source excel` until the futures table is populated.

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

# Daily automation: ingest latest IBKR bars into the DB, then update every
# followed profile (requires [ingest] extra, IB Gateway and DB credentials)
python -m market_intel_pystrat.scripts.run daily
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
