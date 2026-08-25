"""Offline tests of the publish module: fake Slack/S3 clients, no network."""
import pytest

from market_intel_pystrat.publish.publish_data import S3_BUCKET
from market_intel_pystrat.publish.publish_services import (
    format_daily_report,
    publish_run_reports,
    send_slack_message,
    upload_html,
)


def test_format_daily_report_mixed_statuses():
    report = {
        "ingestion": {"SB": "1 inserted, 1 updated"},
        "profiles": {"a": "ok", "b": "error: boom"},
    }
    text = format_daily_report(report)
    assert "✅ ingestion: SB 1 inserted, 1 updated" in text
    assert "✅ a: ok" in text
    assert "❌ b: error: boom" in text


def test_format_daily_report_failed_ingestion():
    report = {"ingestion": "error: gateway down", "profiles": {"a": "skipped (ingestion failed)"}}
    text = format_daily_report(report)
    assert text.startswith("❌ ingestion: error: gateway down")
    assert "❌ a" in text


class _FakeSlack:
    def __init__(self):
        self.posted = []

    def chat_postMessage(self, **kwargs):
        self.posted.append(kwargs)


def test_send_slack_message_uses_env_settings(monkeypatch):
    monkeypatch.setenv("SLACK_TOKEN", "t")
    monkeypatch.setenv("SLACK_CHANNEL", "#chan")
    monkeypatch.setenv("SLACK_USERNAME", "bot")

    fake = _FakeSlack()
    send_slack_message("hello", client=fake)
    assert fake.posted == [{"channel": "#chan", "text": "hello", "username": "bot"}]


def test_send_slack_message_fails_fast_without_settings(monkeypatch):
    for key in ("SLACK_TOKEN", "SLACK_CHANNEL", "SLACK_USERNAME"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="Missing publish settings"):
        send_slack_message("hello", client=_FakeSlack())


class _FakeS3:
    def __init__(self):
        self.uploaded = []

    def upload_file(self, path, bucket, key):
        self.uploaded.append((path, bucket, key))

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        return f"https://s3/{Params['Bucket']}/{Params['Key']}?exp={ExpiresIn}"


def test_upload_html_returns_presigned_url(tmp_path):
    f = tmp_path / "diagnostic.html"
    f.write_text("<html></html>")

    fake = _FakeS3()
    url = upload_html(f, client=fake)

    assert fake.uploaded == [(str(f), S3_BUCKET, "diagnostic.html")]
    assert url.startswith(f"https://s3/{S3_BUCKET}/diagnostic.html")


def test_publish_run_reports_skips_missing_files(tmp_path):
    run_dir = tmp_path / "sb11_zscore"
    run_dir.mkdir()
    (run_dir / "view.html").write_text("<html></html>")
    # diagnostic.html and report.html intentionally absent

    fake = _FakeS3()
    urls = publish_run_reports(run_dir, client=fake)

    assert list(urls) == ["view.html"]
    assert fake.uploaded[0][2] == "sb11_zscore/view.html"
