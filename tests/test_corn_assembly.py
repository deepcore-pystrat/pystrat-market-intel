import pandas as pd

from pystrat.data_source.core import schema

from market_intel_pystrat.data.assembly.corn_assembly_services import assemble_corn_inputs
from market_intel_pystrat.data.profile_inputs_data import (
    CORN_KEY,
    SPOT_ARG_COLUMN,
    SPOT_BRZ_COLUMN,
    SPREAD_COLUMN,
)


def _spot(dates, bids, offers):
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
    inputs = assemble_corn_inputs(
        ohlcv=_ohlcv(FUT_DATES, [100.0, 101.0, 102.0, 103.0]),
        arg=_spot(FUT_DATES, [200.0] * 4, [202.0] * 4),
        brz=_spot(FUT_DATES, [190.0] * 4, [192.0] * 4),
    )
    assert len(inputs.context.clock.index) == 4
    assert CORN_KEY in inputs.specs


def test_spot_ffill_and_spread():
    # Spot quotes missing on the 3rd and 4th futures days: carried forward.
    inputs = assemble_corn_inputs(
        ohlcv=_ohlcv(FUT_DATES, [100.0, 101.0, 102.0, 103.0]),
        arg=_spot(FUT_DATES[:2], [200.0, 204.0], [202.0, 206.0]),
        brz=_spot(FUT_DATES[:2], [190.0, 191.0], [192.0, 193.0]),
    )
    frame = inputs.context.frames[CORN_KEY]
    assert frame[SPOT_ARG_COLUMN].iloc[-1] == 205.0
    assert frame[SPOT_BRZ_COLUMN].iloc[-1] == 192.0
    assert frame[SPREAD_COLUMN].iloc[-1] == 13.0


def test_window_slicing_prevents_seeding():
    # Spot observed only before the window start: must NOT seed the ffill.
    inputs = assemble_corn_inputs(
        ohlcv=_ohlcv(FUT_DATES, [100.0, 101.0, 102.0, 103.0]),
        arg=_spot(["2023-12-29"] + FUT_DATES[2:], [180.0, 200.0, 204.0], [182.0, 202.0, 206.0]),
        brz=_spot(FUT_DATES, [190.0] * 4, [192.0] * 4),
        start="2024-01-01",
        end="2024-12-31",
    )
    frame = inputs.context.frames[CORN_KEY]
    assert frame[SPOT_ARG_COLUMN].iloc[0] != frame[SPOT_ARG_COLUMN].iloc[0]  # NaN
    assert frame[SPOT_ARG_COLUMN].iloc[2] == 201.0