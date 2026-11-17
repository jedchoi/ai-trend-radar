"""업로드 인증 (C-S3, BR-S01). 토큰 원문은 저장 · 기록하지 않는다."""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import HTTPException, Request

from app.logging_setup import log_json, security_log


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def require_ingest_token(request: Request) -> None:
    expected = request.app.state.settings.ingest_token_sha256
    if not expected:
        log_json(security_log, logging.ERROR, event="security_event", kind="ingest_token_unconfigured")
        raise HTTPException(status_code=503)

    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    supplied = hashlib.sha256(token.strip().encode()).hexdigest() if scheme.lower() == "bearer" else ""
    if not supplied or not hmac.compare_digest(supplied, expected):
        log_json(
            security_log,
            logging.WARNING,
            event="security_event",
            kind="auth_failed",
            ip=client_ip(request),
            path=request.url.path,
        )
        raise HTTPException(status_code=401)
