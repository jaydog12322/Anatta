"""Application configuration.

Loads environment variables from a local `.env` file if present.
"""

from __future__ import annotations

import os
from pathlib import Path

# Load variables from `.env` if it exists in the project root.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        if not line or line.strip().startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key and value and key not in os.environ:
            os.environ[key] = value

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
