"""ASGI 미들웨어 (C-S7): 요청 id, 속도 제한, 본문 크기 제한, 보안 헤더, 접근 로그, 최후 오류 처리."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid

from app.logging_setup import access_log, error_log, log_json, security_log

SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
    (b"cache-control", b"no-store"),
]
WINDOW_SECONDS = 60.0


class RateLimiter:
    """IP · 그룹별 고정 창 카운터 (NFR-S05)."""

    def __init__(self, limits: dict[str, int]) -> None:
        self.limits = limits
        self._counts: dict[tuple[str, str], tuple[float, int]] = {}
        self._lock = threading.Lock()

    def allow(self, group: str, ip: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            start, count = self._counts.get((group, ip), (now, 0))
            if now - start >= WINDOW_SECONDS:
                start, count = now, 0
            count += 1
            self._counts[(group, ip)] = (start, count)
            if len(self._counts) > 10000:
                self._counts = {k: v for k, v in self._counts.items() if now - v[0] < WINDOW_SECONDS}
            return count <= self.limits[group]


class GuardMiddleware:
    def __init__(self, app, *, limiter: RateLimiter, max_body_bytes: int) -> None:
        self.app = app
        self.limiter = limiter
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex[:16]
        started = time.perf_counter()
        ip = scope["client"][0] if scope.get("client") else "unknown"
        path = scope["path"]
        state = {"status": 500, "started": False}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                state["status"] = message["status"]
                state["started"] = True
                headers = list(message.get("headers", []))
                headers.extend(SECURITY_HEADERS)
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        async def reply(status: int, code: str) -> None:
            body = json.dumps({"error": code}).encode()
            await send_wrapper(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
                }
            )
            await send_wrapper({"type": "http.response.body", "body": body})

        try:
            group = "ingest" if path.startswith("/api/v1/ingest") else "public"
            if not self.limiter.allow(group, ip):
                log_json(
                    security_log,
                    logging.WARNING,
                    event="security_event",
                    kind="rate_limited",
                    ip=ip,
                    path=path,
                    request_id=request_id,
                )
                await reply(429, "rate_limited")
                return

            headers = dict(scope.get("headers", []))
            length = headers.get(b"content-length")
            if length is not None and (not length.isdigit() or int(length) > self.max_body_bytes):
                await reply(413, "payload_too_large")
                return

            received = 0

            async def receive_limited():
                nonlocal received
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > self.max_body_bytes:
                        raise _BodyTooLarge
                return message

            await self.app(scope, receive_limited, send_wrapper)
        except _BodyTooLarge:
            if not state["started"]:
                await reply(413, "payload_too_large")
        except Exception as exc:  # SECURITY-15: 전역 오류 처리, 내부 정보는 로그에만
            log_json(
                error_log,
                logging.ERROR,
                event="unhandled_error",
                request_id=request_id,
                path=path,
                error=type(exc).__name__,
            )
            if not state["started"]:
                await reply(500, "internal_error")
        finally:
            log_json(
                access_log,
                logging.INFO,
                ts=time.time(),
                request_id=request_id,
                method=scope["method"],
                path=path,
                status=state["status"],
                ip=ip,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )


class _BodyTooLarge(Exception):
    pass
