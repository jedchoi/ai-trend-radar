"""서버 통신 (C-P7, BR-P12): 업로드 · 리포트 · 통계 조회. 토큰은 헤더로만 보낸다."""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx

from radar.models import DigestPayload
from radar.retry import with_retry


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
            return with_retry(lambda: self.http.request(method, path, content=body, headers=headers), self.sleep)
        except httpx.TransportError as exc:
            raise UploadError(f"서버 연결 실패 ({type(exc).__name__})") from exc

    def upload_digest(self, payload: DigestPayload) -> None:
        response = self._request("POST", "/api/v1/ingest/daily", payload.model_dump_json())
        if response.status_code != 200:
            raise UploadError(f"업로드 실패: HTTP {response.status_code}", response.status_code)

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
