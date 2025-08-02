"""Logging utilities with Slack integration."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config.settings import SLACK_WEBHOOK_URL


INTERNAL_LOGGER_NAME = "slack"
_internal_logger = logging.getLogger(INTERNAL_LOGGER_NAME)
_internal_logger.setLevel(logging.WARNING)
_internal_logger.propagate = False
if not _internal_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    _internal_logger.addHandler(_handler)


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
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(
                    request, timeout=5
            ) as response:  # noqa: S310
                response.read()
        except HTTPError:
            # Avoid raising exceptions during logging.
            pass
        except URLError as error:
            if isinstance(getattr(error, "reason", None), TimeoutError):
                _internal_logger.warning("Slack webhook request timed out")
            # Avoid raising exceptions during logging.
            pass
        except TimeoutError:
            _internal_logger.warning("Slack webhook request timed out")

def get_logger(name: str = __name__) -> logging.Logger:
    """Return a logger configured with Slack webhook integration."""
    if name == INTERNAL_LOGGER_NAME:
        return _internal_logger

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        slack_handler = SlackWebhookHandler()
        slack_handler.setFormatter(formatter)
        logger.addHandler(slack_handler)

    return logger
