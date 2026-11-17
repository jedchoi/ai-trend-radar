"""JSON 한 줄 로그 (NFR-S08)."""

from __future__ import annotations

import json
import logging
import sys

access_log = logging.getLogger("radar.access")
security_log = logging.getLogger("radar.security")
error_log = logging.getLogger("radar.error")


def log_json(logger: logging.Logger, level: int, **fields) -> None:
    logger.log(level, json.dumps(fields, ensure_ascii=False, default=str))


def configure() -> None:
    root = logging.getLogger("radar")
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
