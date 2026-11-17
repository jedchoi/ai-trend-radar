"""서버 통신 (C-P7, BR-P12): 업로드 · 리포트 · 통계 조회. 토큰은 헤더로만 보낸다."""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx

from radar.models import DigestPayload
from radar.retry import with_retry

RATE_LIMIT_RETRIES = 3
NEWS_BATCH = 10  # BR-P33
RATE_LIMIT_MAX_WAIT_S = 120


def _retry_after(response: httpx.Response) -> int:
    try:
        return max(1, min(RATE_LIMIT_MAX_WAIT_S, int(response.headers.get("retry-after", "60"))))
    except ValueError:
        return 60


class UploadError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class ServerClient:
    def __init__(self, http: httpx.Client, token: str, sleep: Callable[[float], None] = time.sleep) -> None:
        self.http = http
        self.token = token
        self.sleep = sleep

    def _request(self, method: str, path: str, body: str | None = None) -> httpx.Response:
        headers = {"authorization": f"Bearer {self.token}"}
        if body is not None:
            headers["content-type"] = "application/json"
        try:
            response = with_retry(lambda: self.http.request(method, path, content=body, headers=headers), self.sleep)
            for _ in range(RATE_LIMIT_RETRIES):  # 백필처럼 업로드가 몰리면 서버가 알려준 만큼 기다린다
                if response.status_code != 429:
                    break
                self.sleep(_retry_after(response))
                response = self.http.request(method, path, content=body, headers=headers)
            return response
        except httpx.TransportError as exc:
            raise UploadError(f"서버 연결 실패 ({type(exc).__name__})") from exc

    def upload_digest(self, payload: DigestPayload) -> None:
        response = self._request("POST", "/api/v1/ingest/daily", payload.model_dump_json())
        if response.status_code != 200:
            raise UploadError(f"업로드 실패: HTTP {response.status_code}", response.status_code)

    def upload_news(self, items: list[dict], provider: str) -> int:
        """BR-P33: 10건씩. 한 묶음이라도 실패하면 UploadError (앞 묶음은 이미 저장됨)."""
        import json

        sent = 0
        for start in range(0, len(items), NEWS_BATCH):
            batch = items[start : start + NEWS_BATCH]
            body = json.dumps({"provider": provider, "items": batch}, ensure_ascii=False)
            response = self._request("POST", "/api/v1/ingest/news", body)
            if response.status_code != 200:
                raise UploadError(f"뉴스 업로드 실패: HTTP {response.status_code}", response.status_code)
            sent += len(batch)
        return sent

    def upload_report(self, period: str, key: str, narrative: str, provider: str) -> None:
        import json

        body = json.dumps(
            {"period": period, "key": key, "narrative": narrative, "provider": provider}, ensure_ascii=False
        )
        response = self._request("POST", "/api/v1/ingest/report", body)
        if response.status_code != 200:
            raise UploadError(f"리포트 업로드 실패: HTTP {response.status_code}", response.status_code)

    def fetch_stats(self, period: str, key: str) -> dict | None:
        path = f"/api/v1/trends/{'weekly' if period == 'week' else 'monthly'}/{key}"
        response = self._request("GET", path)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise UploadError(f"통계 조회 실패: HTTP {response.status_code}", response.status_code)
        return response.json()

    def health(self) -> dict:
        response = self._request("GET", "/api/v1/health")
        if response.status_code != 200:
            raise UploadError(f"health: HTTP {response.status_code}", response.status_code)
        return response.json()
