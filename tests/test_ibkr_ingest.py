"""Offline tests of the IBKR ingestion chain: fake fetch/execute, no DB, no gateway."""
import pandas as pd
import pytest

from pystrat.data_source.connectors.postgres_connector_data import PostgresConfig

from market_intel_pystrat.data.ibkr.ibkr_data import (
    INSERT_FUTURES_QUERY,
    SELECT_EXISTING_DATES_QUERY,
    UPDATE_FUTURES_QUERY,
)
from market_intel_pystrat.data.ibkr.ibkr_services import (
    normalize_daily_bars,
    to_db_cents,
    upsert_futures_bars,
)

_CONFIG = PostgresConfig(host="h", database="d", username="u", password="p")


def _bars(dates, close=13.92):
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "open": 13.50, "high": 14.00, "low": 13.40,
        "close": close, "volume": 1000,
    })


def test_to_db_cents_matches_storage_convention():
    assert to_db_cents(13.92) == "1392"
    assert to_db_cents(3000.0) == "300000"


def test_normalize_dedupes_and_drops_missing_close():
    bars = _bars(["2026-08-20", "2026-08-20", "2026-08-21"], close=[13.0, 13.5, None])
    out = normalize_daily_bars(bars)
    # duplicate 08-20 keeps last; 08-21 dropped (no close)
    assert len(out) == 1
    assert out["close"].iloc[0] == 13.5


def test_normalize_rejects_missing_columns():
    with pytest.raises(ValueError, match="missing required column"):
        normalize_daily_bars(pd.DataFrame({"date": [], "close": []}))


def test_upsert_splits_inserts_and_updates():
    calls = []

    def fake_fetch(config, query, params):
        assert query == SELECT_EXISTING_DATES_QUERY
        assert params == ("sb11", "2026-08-20")
        return pd.DataFrame({"date": [pd.Timestamp("2026-08-20")]})  # 08-20 already in DB

    def fake_execute(config, statement, rows):
        calls.append((statement, list(rows)))
        return len(rows)

    bars = _bars(["2026-08-20", "2026-08-21"])
    inserted, updated = upsert_futures_bars(
        _CONFIG, "sb11", bars, fetch=fake_fetch, execute=fake_execute
    )

    assert (inserted, updated) == (1, 1)
    statements = {stmt for stmt, _ in calls}
    assert statements == {INSERT_FUTURES_QUERY, UPDATE_FUTURES_QUERY}

    insert_rows = next(rows for stmt, rows in calls if stmt == INSERT_FUTURES_QUERY)
    name, date, open_, high, low, close, volume, _, _ = insert_rows[0]
    assert (name, date) == ("sb11", "2026-08-21")
    assert close == "1392" and volume == "1000"

    update_rows = next(rows for stmt, rows in calls if stmt == UPDATE_FUTURES_QUERY)
    assert update_rows[0][-2:] == ("sb11", "2026-08-20")


def test_upsert_empty_bars_touches_nothing():
    def boom(*args):
        raise AssertionError("should not be called")

    bars = _bars([]).astype({"date": "datetime64[ns]"})
    assert upsert_futures_bars(_CONFIG, "corn", bars, fetch=boom, execute=boom) == (0, 0)
