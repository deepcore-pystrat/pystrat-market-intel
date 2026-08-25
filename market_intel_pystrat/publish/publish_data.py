from __future__ import annotations

# Same env keys and bucket as the legacy platform, for a drop-in hookup.
S3_BUCKET = "thedeepcore"
PRESIGNED_URL_EXPIRY_SECONDS = 86400 * 5

SLACK_ENV_KEYS = ("SLACK_TOKEN", "SLACK_CHANNEL", "SLACK_USERNAME")
AWS_ENV_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION")
