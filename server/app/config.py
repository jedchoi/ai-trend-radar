"""환경 변수 설정 (logical-components.md: Settings)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


@dataclass(frozen=True)
class Settings:
    db_path: str = "/data/radar.db"
    ingest_token_sha256: str = ""
    enable_docs: bool = False
    public_rate_per_min: int = 120
    ingest_rate_per_min: int = 30
    max_body_bytes: int = 2 * 1024 * 1024

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            db_path=os.environ.get("DB_PATH", cls.db_path),
            ingest_token_sha256=os.environ.get("INGEST_TOKEN_SHA256", "").strip().lower(),
            enable_docs=os.environ.get("ENABLE_DOCS", "0") == "1",
            public_rate_per_min=_int("PUBLIC_RATE_PER_MIN", cls.public_rate_per_min),
            ingest_rate_per_min=_int("INGEST_RATE_PER_MIN", cls.ingest_rate_per_min),
            max_body_bytes=_int("MAX_BODY_BYTES", cls.max_body_bytes),
        )
