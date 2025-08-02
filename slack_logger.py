"""Logging utilities with Slack integration."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config.settings import SLACK_WEBHOOK_URL


class SlackWebhookHandler(logging.Handler):
    """Logging handler that posts messages to a Slack Incoming Webhook."""

    def emit(self, record: logging.LogRecord) -> None:
        webhook_url = SLACK_WEBHOOK_URL
        if not webhook_url:
            # No webhook configured; skip sending.
            return

        log_entry = self.format(record)
        data = json.dumps({"text": log_entry}).encode("utf-8")
        request = Request(
            webhook_url, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urlopen(request) as response:  # noqa: S310 (urllib urlopen is safe here)
                response.read()
        except (HTTPError, URLError):
            # Avoid raising exceptions during logging.
            pass


def get_logger(name: str = __name__) -> logging.Logger:
    """Return a logger configured with Slack webhook integration."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        slack_handler = SlackWebhookHandler()
        slack_handler.setFormatter(formatter)
        logger.addHandler(slack_handler)

    return logger

#