"""DeepCore DB tests: pure parser tests + a real-connection smoke (skipped
when no credentials are available)."""
import pandas as pd
import pytest

from market_intel_pystrat.data.deepcore_db.deepcore_db_services import (
    coffee_spot_source,
    futures_source,
    load_deepcore_config,
    parse_futures_frame,
    parse_quotations_frame,
    spot_source,
    parse_coffee_frame
)


def test_parse_futures_frame():
    raw = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-01"],
            "open": [10, 9],
            "high": [11, 10],
            "low": [9, 8],
            "close": ["1050", "950"],  # stored x100, string on purpose: coercion
            "volume": [100, 90],
        }
    )
    bars = parse_futures_frame(raw)
    assert isinstance(bars.index, pd.DatetimeIndex)
    assert bars.index.is_monotonic_increasing
    assert bars["close"].iloc[0] == 9.5
    assert bars["volume"].iloc[0] == 90  # volume NOT scaled (legacy divided it too)


def test_parse_quotations_frame():
    raw = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-01"],
            "bid": [1.0, None],
            "offer": ["1.2", 1.1],
        }
    )
    basis = parse_quotations_frame(raw)
    assert isinstance(basis.index, pd.DatetimeIndex)
    assert basis.index.is_monotonic_increasing
    assert basis["offer"].iloc[1] == 1.2


def test_source_builders_reject_unknown_assets():
    with pytest.raises(KeyError):
        futures_source("GOLD")
    with pytest.raises(KeyError):
        spot_source("XXX")


def _config_or_none():
    try:
        return load_deepcore_config()
    except (ValueError, ImportError):
        return None


@pytest.mark.skipif(_config_or_none() is None, reason="no DeepCore credentials")
def test_deepcore_connection_smoke():
    """Fetch a few real rows from both tables through the generic provider."""
    from pystrat.data_source.providers.postgres_provider import PostgresProvider

    provider = PostgresProvider(
        config=load_deepcore_config(),
        sources={
            "SB11": futures_source("SB11"),
            "BASIS_VHP": spot_source("VHP"),
        },
    )
    bars = provider.get_data("SB11")
    basis = provider.get_data("BASIS_VHP")
    assert len(bars) > 0 and "close" in bars.columns
    assert len(basis) > 0 and {"bid", "offer"} <= set(basis.columns)

def test_parse_coffee_frame():
    raw = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-01", "2024-01-01"],
            "origin": ["Vietnam", "Vietnam", "Uganda"],
            "bid": [100, 90, None],
            "offer": ["102", 92, 80],
        }
    )
    basis = parse_coffee_frame(raw)
    assert list(basis.columns) == ["origin", "value"]
    assert basis["value"].iloc[-1] == 101.0   # mid of 100/102
    assert basis["value"].iloc[1] == 80.0     # offer only -> offer
    assert basis["value"].iloc[0] == 91.0     # mid of 90/92

def test_coffee_source_rejects_unknown():
    with pytest.raises(KeyError):
        coffee_spot_source("COFFEE_XXX")