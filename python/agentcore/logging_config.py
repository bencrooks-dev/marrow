"""Structured logging helper.

Configures the ``agentcore`` logger family to emit JSON lines. Opt-in;
the library itself uses Python's standard logging module and emits
nothing if you don't configure a handler.

Usage::

    import agentcore.logging_config as lc
    lc.configure_json(level="INFO")

    import logging
    logging.getLogger("agentcore").info("started")
"""
from __future__ import annotations

import json
import logging
from typing import Any


class JsonFormatter(logging.Formatter):
    """One-line JSON per record. Includes any extras attached via the
    LoggerAdapter `extra=` dict."""

    _STD_FIELDS = {
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": record.created,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k in self._STD_FIELDS or k.startswith("_"):
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except (TypeError, ValueError):
                payload[k] = repr(v)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_json(level: str | int = "INFO", logger_name: str = "agentcore") -> None:
    """Install a JSON handler on the named logger. Idempotent — if the
    logger already has a JSON handler, do nothing."""
    logger = logging.getLogger(logger_name)
    if any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level if isinstance(level, int) else level.upper())
    logger.propagate = False  # don't double-log via root
