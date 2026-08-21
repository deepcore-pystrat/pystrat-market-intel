import pandas as pd

from pystrat.data_source.core import schema

from market_intel_pystrat.data.assembly.sb11_assembly_services import assemble_sb11_basis_inputs
from market_intel_pystrat.data.profile_inputs_data import (
    BASIS_THP_COLUMN,
    BASIS_VHP_COLUMN,
    SB11_KEY,
)


def _quotes(dates, bids, offers):
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    return pd.DataFrame({schema.BID: bids, schema.OFFER: offers}, index=idx)


def _ohlcv(dates, closes):
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    return pd.DataFrame(
        {"open": closes, "high": closes, "low": closes, "close": closes, "volume": 0},
        index=idx,
    )


FUT_DATES = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]


def test_clock_is_futures_days():
    inputs = assemble_sb11_basis_inputs(
        ohlcv=_ohlcv(FUT_DATES, [20.0, 21.0, 22.0, 23.0]),
        vhp=_quotes(FUT_DATES, [1.0] * 4, [1.2] * 4),
        thp=_quotes(FUT_DATES, [0.5] * 4, [0.7] * 4),
    )
    assert len(inputs.context.clock.index) == 4
    assert SB11_KEY in inputs.specs
    assert SB11_KEY in inputs.price_frames


def test_one_sided_quote_uses_last_known_side_and_carries():
    # Day 2: bid missing -> per-side fill uses the LAST bid (1.0), never the
    # same-day offer. Days 3-4: no quote row -> as-of carries day 2's mid.
    inputs = assemble_sb11_basis_inputs(
        ohlcv=_ohlcv(FUT_DATES, [20.0, 21.0, 22.0, 23.0]),
        vhp=_quotes(FUT_DATES[:2], [1.0, None], [1.4, 1.6]),
        thp=_quotes(FUT_DATES, [0.5] * 4, [0.7] * 4),
    )
    frame = inputs.context.frames[SB11_KEY]
    assert frame[BASIS_VHP_COLUMN].iloc[0] == 1.2   # (1.0 + 1.4) / 2
    assert frame[BASIS_VHP_COLUMN].iloc[1] == 1.3   # (1.0 carried + 1.6) / 2, not 1.6
    assert frame[BASIS_VHP_COLUMN].iloc[3] == 1.3   # as-of carry over quoteless days


def test_window_slicing_prevents_seeding():
    # Quote observed only before the window start: must NOT seed the ffill.
    inputs = assemble_sb11_basis_inputs(
        ohlcv=_ohlcv(FUT_DATES, [20.0, 21.0, 22.0, 23.0]),
        vhp=_quotes(["2023-12-29"] + FUT_DATES[2:], [0.8, 1.0, 1.2], [1.0, 1.4, 1.6]),
        thp=_quotes(FUT_DATES, [0.5] * 4, [0.7] * 4),
        start="2024-01-01",
        end="2024-12-31",
    )
    frame = inputs.context.frames[SB11_KEY]
    assert frame[BASIS_VHP_COLUMN].iloc[0] != frame[BASIS_VHP_COLUMN].iloc[0]  # NaN
    assert frame[BASIS_VHP_COLUMN].iloc[1] != frame[BASIS_VHP_COLUMN].iloc[1]  # NaN
    assert frame[BASIS_VHP_COLUMN].iloc[2] == 1.2   # (1.0 + 1.4) / 2, in-window only