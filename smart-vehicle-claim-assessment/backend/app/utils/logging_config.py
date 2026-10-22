from __future__ import annotations

import logging
import sys
from typing import Optional

from app.config import get_settings


class ClaimContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "claim_id"):
            record.claim_id = "-"
        return True


def configure_logging(level: Optional[str] = None) -> None:
    settings = get_settings()
    log_level = (level or settings.log_level).upper()
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ClaimContextFilter())
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s claim=%(claim_id)s operation=%(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level, logging.INFO))
