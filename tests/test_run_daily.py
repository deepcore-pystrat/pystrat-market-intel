"""Offline tests of the daily orchestrator: ingestion and updates are faked."""
import pytest

import market_intel_pystrat.jobs.run.run_daily as rd


def test_profile_failure_does_not_stop_the_others(monkeypatch):
    monkeypatch.setattr(rd, "fetch_and_upsert", lambda duration: {"SB": (1, 1)})
    calls = []

    def fake_update(name, run_dir, data_dir=None, *, source):
        calls.append((name, source))
        if name == "b":
            raise ValueError("boom")
        return run_dir

    monkeypatch.setattr(rd, "run_update", fake_update)
    report = rd.run_daily(profiles=("a", "b", "c"))

    assert [c[0] for c in calls] == ["a", "b", "c"]
    assert all(source == "postgres" for _, source in calls)
    assert report["profiles"]["a"] == "ok"
    assert report["profiles"]["b"] == "error: boom"
    assert report["profiles"]["c"] == "ok"
    assert report["ingestion"] == {"SB": "1 inserted, 1 updated"}
    assert rd.has_failures(report)


def test_ingestion_failure_skips_all_updates(monkeypatch):
    def broken_ingest(duration):
        raise ConnectionError("gateway down")

    def never_called(*args, **kwargs):
        raise AssertionError("run_update must not run after a failed ingestion")

    monkeypatch.setattr(rd, "fetch_and_upsert", broken_ingest)
    monkeypatch.setattr(rd, "run_update", never_called)

    report = rd.run_daily(profiles=("a", "b"))
    assert report["ingestion"] == "error: gateway down"
    assert report["profiles"] == {
        "a": "skipped (ingestion failed)",
        "b": "skipped (ingestion failed)",
    }
    assert rd.has_failures(report)


def test_skip_ingest_runs_updates_only(monkeypatch):
    def never_called(*args, **kwargs):
        raise AssertionError("ingestion must not run with ingest=False")

    monkeypatch.setattr(rd, "fetch_and_upsert", never_called)
    monkeypatch.setattr(rd, "run_update", lambda name, run_dir, data_dir=None, *, source: run_dir)

    report = rd.run_daily(profiles=("a",), ingest=False)
    assert report["ingestion"] == "skipped"
    assert report["profiles"] == {"a": "ok"}
    assert not rd.has_failures(report)
