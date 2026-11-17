"""환경 변수 설정 (logical-components.md: Settings)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


@dataclass(frozen=True)
class Settings:
    database_url: str = "postgresql://radar@localhost:5432/radar"
    db_pool_size: int = 5
    ingest_token_sha256: str = ""
    enable_docs: bool = False
    public_rate_per_min: int = 120
    ingest_rate_per_min: int = 30
    max_body_bytes: int = 10 * 1024 * 1024  # BR-S34: 원문이 든 업로드

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.environ.get("DATABASE_URL", cls.database_url),
            db_pool_size=_int("DB_POOL_SIZE", cls.db_pool_size),
            ingest_token_sha256=os.environ.get("INGEST_TOKEN_SHA256", "").strip().lower(),
            enable_docs=os.environ.get("ENABLE_DOCS", "0") == "1",
            public_rate_per_min=_int("PUBLIC_RATE_PER_MIN", cls.public_rate_per_min),
            ingest_rate_per_min=_int("INGEST_RATE_PER_MIN", cls.ingest_rate_per_min),
            max_body_bytes=_int("MAX_BODY_BYTES", cls.max_body_bytes),
        )
