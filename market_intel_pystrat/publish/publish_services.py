from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Union

from market_intel_pystrat.data.deepcore_db.deepcore_db_services import DEFAULT_ENV_PATH
from market_intel_pystrat.publish.publish_data import (
    AWS_ENV_KEYS,
    PRESIGNED_URL_EXPIRY_SECONDS,
    S3_BUCKET,
    SLACK_ENV_KEYS,
)


def _load_env_values(keys: Sequence[str], env_path: Optional[Union[str, Path]] = None) -> Dict[str, str]:
    """Read the requested keys from .env and/or environment variables; raise if any is missing."""
    from dotenv import dotenv_values

    values = dict(os.environ)
    path = Path(env_path) if env_path is not None else DEFAULT_ENV_PATH
    if path.exists():
        values.update({k: v for k, v in dotenv_values(path).items() if v is not None})

    missing = [k for k in keys if not values.get(k)]
    if missing:
        raise ValueError(
            f"Missing publish settings {missing}; set them in {path} or as environment variables."
        )
    return {k: values[k] for k in keys}


# --- Slack ---

def send_slack_message(
    text: str,
    *,
    env_path: Optional[Union[str, Path]] = None,
    client=None,
) -> None:
    """Post a message to the team Slack channel (SLACK_TOKEN/CHANNEL/USERNAME).

    `client` is injectable for tests; by default a slack_sdk WebClient is built.
    """
    values = _load_env_values(SLACK_ENV_KEYS, env_path)
    if client is None:
        try:
            from slack_sdk import WebClient
        except ImportError as exc:
            raise ImportError(
                "slack_sdk is required for Slack notifications. "
                "Install it with: pip install market_intel_pystrat[publish]"
            ) from exc
        client = WebClient(token=values["SLACK_TOKEN"])

    client.chat_postMessage(
        channel=values["SLACK_CHANNEL"],
        text=text,
        username=values["SLACK_USERNAME"],
    )


def format_daily_report(report: Mapping) -> str:
    """Turn a run_daily report dict into a compact Slack message."""
    lines = []
    ingestion = report["ingestion"]
    if isinstance(ingestion, str):
        icon = "❌" if ingestion.startswith("error") else "▫️"
        lines.append(f"{icon} ingestion: {ingestion}")
    else:
        detail = ", ".join(f"{asset} {counts}" for asset, counts in ingestion.items())
        lines.append(f"✅ ingestion: {detail}")

    for name, status in report["profiles"].items():
        icon = "✅" if status == "ok" else "❌"
        lines.append(f"{icon} {name}: {status}")
    return "\n".join(lines)


# --- S3 ---

def _build_s3_client(env_path: Optional[Union[str, Path]] = None):
    try:
        import boto3
    except ImportError as exc:
        raise ImportError(
            "boto3 is required for S3 uploads. "
            "Install it with: pip install market_intel_pystrat[publish]"
        ) from exc
    values = _load_env_values(AWS_ENV_KEYS, env_path)
    session = boto3.Session(
        aws_access_key_id=values["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=values["AWS_SECRET_ACCESS_KEY"],
        region_name=values["AWS_REGION"],
    )
    return session.client("s3")


def upload_html(
    local_path: Union[str, Path],
    key: Optional[str] = None,
    *,
    env_path: Optional[Union[str, Path]] = None,
    client=None,
) -> str:
    """Upload one HTML file to the team bucket and return a presigned URL (5 days).

    `key` defaults to the file name. `client` is injectable for tests.
    """
    local_path = Path(local_path)
    if key is None:
        key = local_path.name
    if client is None:
        client = _build_s3_client(env_path)

    client.upload_file(str(local_path), S3_BUCKET, key)
    return client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=PRESIGNED_URL_EXPIRY_SECONDS,
    )


def publish_run_reports(
    run_dir: Union[str, Path],
    *,
    files: Sequence[str] = ("diagnostic.html", "view.html", "report.html"),
    env_path: Optional[Union[str, Path]] = None,
    client=None,
) -> Dict[str, str]:
    """Upload a run's HTML reports to S3; returns {file_name: presigned_url}.

    Keys are prefixed with the run directory name (e.g. 'sb11_zscore/view.html').
    Missing files are skipped silently.
    """
    run_dir = Path(run_dir)
    if client is None:
        client = _build_s3_client(env_path)

    urls: Dict[str, str] = {}
    for name in files:
        f = run_dir / name
        if f.exists():
            urls[name] = upload_html(f, key=f"{run_dir.name}/{name}", client=client)
    return urls
