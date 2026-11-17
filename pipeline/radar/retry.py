"""외부 호출 재시도 (BR-P02, BR-P12): 네트워크 오류 · 429 · 5xx 만, 최대 3회 (대기 2초, 4초)."""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx

DELAYS = (2, 4)


def is_retryable(status: int) -> bool:
    return status == 429 or status >= 500


def with_retry(call: Callable[[], httpx.Response], sleep: Callable[[float], None] = time.sleep) -> httpx.Response:
    """마지막 응답을 돌려주고, 세 번 모두 네트워크 오류면 마지막 예외를 다시 던진다."""
    last_error: Exception | None = None
    for attempt in range(len(DELAYS) + 1):
        try:
            response = call()
            if not is_retryable(response.status_code) or attempt == len(DELAYS):
                return response
        except httpx.TransportError as exc:
            last_error = exc
            if attempt == len(DELAYS):
                raise
        sleep(DELAYS[attempt])
    raise RuntimeError("unreachable") from last_error  # pragma: no cover
