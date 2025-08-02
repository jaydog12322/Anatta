"""Application configuration.

Loads environment variables from a local `.env` file if present.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from `.env` if it exists in the project root.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")