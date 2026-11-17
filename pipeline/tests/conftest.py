import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest

from radar.config import AIConfig, CollectConfig, Config, PathsConfig, SelectConfig, ServerConfig, TranslateConfig


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
        fail_dates: set | None = None,
        pages: dict | None = None,
    ):
        self.days = days or {}
        self.trending = trending or {"models": [], "datasets": [], "spaces": []}
        self.markdown = markdown or {}
        self.fail = fail or {}  # path → [status, ...] 순서대로 먼저 반환
        self.fail_dates = fail_dates or set()  # 이 날짜의 daily_papers 는 항상 500
        self.pages = pages or {}  # 경로 → 본문 (블로그 RSS · 글 HTML)
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, params = request.url.path, dict(request.url.params)
        self.calls.append(f"{path}?{request.url.query.decode()}")
        if self.fail.get(path):
            return httpx.Response(self.fail[path].pop(0))
        if path == "/api/daily_papers" and params.get("date") in self.fail_dates:
            return httpx.Response(500)
        if path == "/api/daily_papers":
            items = self.days.get(params["date"], [])
            p, limit = int(params.get("p", 0)), int(params["limit"])
            return httpx.Response(200, json=items[p * limit : (p + 1) * limit])
        if path in ("/api/models", "/api/datasets", "/api/spaces"):
            kind = path.rsplit("/", 1)[1]
            return httpx.Response(200, json=self.trending[kind][: int(params["limit"])])
        if path in self.pages:
            return httpx.Response(200, text=self.pages[path])
        if path.startswith("/papers/") and path.endswith(".md"):
            pid = path[len("/papers/") : -3]
            if pid in self.markdown:
                return httpx.Response(200, text=self.markdown[pid])
            return httpx.Response(404)
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler), base_url="https://huggingface.co")


class FakeServer:
    def __init__(self, statuses: list[int] | None = None, stats: dict | None = None, pages: dict | None = None):
        self.statuses = statuses or []
        self.stats = stats or {}
        self.pages = pages or {}  # GET 경로 → JSON (번역 단계가 읽는 공개 API)
        self.translations: list[dict] = []
        self.uploads: list[dict] = []
        self.reports: list[dict] = []
        self.news: list[dict] = []
        self.events: list[tuple] = []  # 업로드 순서 (종류, 키, 제공자)
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
            self.events.append(("daily", body["date"], body["provider"]))
            return httpx.Response(200, json={"date": body["date"], "papers": len(body["papers"])})
        if request.method == "POST" and path == "/api/v1/ingest/news":
            body = json.loads(request.content)
            self.news.append(body)
            self.events.append(("news", len(body["items"]), body["provider"]))
            return httpx.Response(200, json={"news": len(body["items"])})
        if request.method == "POST" and path == "/api/v1/ingest/report":
            self.reports.append(json.loads(request.content))
            return httpx.Response(200, json={})
        if request.method == "POST" and path == "/api/v1/ingest/translations":
            body = json.loads(request.content)
            self.translations.append(body)
            self.events.append(("translations", len(body["items"]), body["provider"]))
            return httpx.Response(200, json={"translations": len(body["items"])})
        if request.method == "GET" and path in self.pages:
            return httpx.Response(200, json=self.pages[path])
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
        # 1주기 테스트는 원문 · 뉴스 없이 (2주기 기능은 test_news.py · test_fulltext.py 가 켜서 검사)
        collect=CollectConfig(models=2, datasets=1, spaces=1, full_text=False, news=False),
        select=SelectConfig(max_featured=2, focus_topics=["agents"]),
        paths=PathsConfig(data_dir=str(tmp_path / "data")),
        translate=TranslateConfig(enabled=False),  # 3주기 기능은 test_translate.py 가 켜서 검사
    )


@pytest.fixture(autouse=True)
def token_env(monkeypatch):
    monkeypatch.setenv("RADAR_TEST_TOKEN", "secret-token-value")


KST_NOON = dt.datetime(2026, 11, 17, 3, 0, tzinfo=dt.UTC)  # 한국 시간 2026-11-17 (화) 12:00


SERVER_SCHEMAS = Path(__file__).resolve().parents[2] / "server" / "app" / "schemas.py"


@pytest.fixture(scope="session")
def contract():
    """서버 계약 (server/app/schemas.py) 을 직접 읽는다."""
    if not SERVER_SCHEMAS.exists():
        pytest.skip("server/ 없음")
    spec = importlib.util.spec_from_file_location("server_schemas", SERVER_SCHEMAS)
    module = importlib.util.module_from_spec(spec)
    sys.modules["server_schemas"] = module
    spec.loader.exec_module(module)
    return module
