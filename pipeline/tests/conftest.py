import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from radar.config import AIConfig, CollectConfig, Config, PathsConfig, SelectConfig, ServerConfig


def hf_item(pid: str, **kw) -> dict:
    """Hugging Face Daily Papers 항목 모양 (2026-11 실제 응답의 필드 이름)."""
    paper = {
        "id": pid,
        "authors": [{"name": "Kim"}, {"name": "Lee", "hidden": False}],
        "publishedAt": "2026-11-11T00:00:00.000Z",
        "title": kw.pop("title", f"Paper {pid}"),
        "summary": kw.pop("abstract", f"We study {pid}. It works well."),
        "upvotes": kw.pop("upvotes", 10),
        "ai_summary": kw.pop("ai_summary", f"AI summary of {pid}."),
        "ai_keywords": kw.pop("ai_keywords", ["Reasoning"]),
        "githubRepo": kw.pop("github", None),
        "githubStars": kw.pop("stars", None),
        "projectPage": kw.pop("project", None),
        "organization": kw.pop("organization", None),
    }
    paper.update(kw)
    return {"paper": paper, "publishedAt": "2026-11-12T19:00:00.000Z", "title": paper["title"], "numComments": 0}


class FakeHF:
    def __init__(
        self,
        days: dict[str, list[dict]] | None = None,
        trending: dict | None = None,
        markdown: dict | None = None,
        fail: dict | None = None,
    ):
        self.days = days or {}
        self.trending = trending or {"models": [], "datasets": [], "spaces": []}
        self.markdown = markdown or {}
        self.fail = fail or {}  # path → [status, ...] 순서대로 먼저 반환
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, params = request.url.path, dict(request.url.params)
        self.calls.append(f"{path}?{request.url.query.decode()}")
        if self.fail.get(path):
            return httpx.Response(self.fail[path].pop(0))
        if path == "/api/daily_papers":
            items = self.days.get(params["date"], [])
            p, limit = int(params.get("p", 0)), int(params["limit"])
            return httpx.Response(200, json=items[p * limit : (p + 1) * limit])
        if path in ("/api/models", "/api/datasets", "/api/spaces"):
            kind = path.rsplit("/", 1)[1]
            return httpx.Response(200, json=self.trending[kind][: int(params["limit"])])
        if path.startswith("/papers/") and path.endswith(".md"):
            pid = path[len("/papers/") : -3]
            if pid in self.markdown:
                return httpx.Response(200, text=self.markdown[pid])
            return httpx.Response(404)
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler), base_url="https://huggingface.co")


class FakeServer:
    def __init__(self, statuses: list[int] | None = None, stats: dict | None = None):
        self.statuses = statuses or []
        self.stats = stats or {}
        self.uploads: list[dict] = []
        self.reports: list[dict] = []
        self.auth: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.auth.append(request.headers.get("authorization", ""))
        if self.statuses:
            status = self.statuses.pop(0)
            if status != 200:
                return httpx.Response(status, json={"error": "x"})
        path = request.url.path
        if request.method == "POST" and path == "/api/v1/ingest/daily":
            body = json.loads(request.content)
            self.uploads.append(body)
            return httpx.Response(200, json={"date": body["date"], "papers": len(body["papers"])})
        if request.method == "POST" and path == "/api/v1/ingest/report":
            self.reports.append(json.loads(request.content))
            return httpx.Response(200, json={})
        if request.method == "GET" and path.startswith("/api/v1/trends/"):
            key = path.rsplit("/", 1)[1]
            if key in self.stats:
                return httpx.Response(200, json=self.stats[key])
            return httpx.Response(404, json={"error": "not_found"})
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler), base_url="https://radar.example.com")


class ScriptedProvider:
    """AI 제공자 대역: 프롬프트 이름 (system 첫 줄) 별로 응답 함수를 돌려준다."""

    name = "fake"

    def __init__(self, responders: dict):
        self.responders = responders
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        kind = system.splitlines()[0].strip()
        self.calls.append((kind, user))
        responder = self.responders[kind]
        return responder(user) if callable(responder) else responder.pop(0)


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        server=ServerConfig(url="https://radar.example.com", token_env="RADAR_TEST_TOKEN"),
        ai=AIConfig(provider="none"),
        collect=CollectConfig(models=2, datasets=1, spaces=1),
        select=SelectConfig(max_featured=2, focus_topics=["agents"]),
        paths=PathsConfig(data_dir=str(tmp_path / "data")),
    )


@pytest.fixture(autouse=True)
def token_env(monkeypatch):
    monkeypatch.setenv("RADAR_TEST_TOKEN", "secret-token-value")


KST_NOON = dt.datetime(2026, 11, 17, 3, 0, tzinfo=dt.UTC)  # 한국 시간 2026-11-17 (화) 12:00
