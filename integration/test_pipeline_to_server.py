"""통합 테스트 (Build and Test): PC 파이프라인 → 실제 HTTP → backend 서버 → 앱이 읽는 API.

실행: PYTHONPATH=server:pipeline pytest integration -q  (PostgreSQL: TEST_DATABASE_URL, 기본 tool/test-db.sh 의 주소)
Hugging Face 는 가짜 응답 (MockTransport), 서버는 uvicorn 으로 실제 포트에서 띄운다.
"""

import datetime as dt
import hashlib
import json
import os
import socket
import threading
import time

import httpx
import psycopg
import pytest
import uvicorn

from app.config import Settings
from app.main import create_app
from app.repository import TABLES, Repository
from radar.analyze import Analyzer
from radar.config import AIConfig, CollectConfig, Config, PathsConfig, SelectConfig, ServerConfig
from radar.hf_client import HFClient
from radar.publish import ServerClient
from radar.runner import EXIT_OK, Runner

TOKEN = "integration-token-0123456789abcdef"
DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://radar@127.0.0.1:55432/radar_test")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server(tmp_path):
    repo = Repository(DATABASE_URL)
    repo.init(wait_s=3)
    repo.close()
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY")
    port = free_port()
    settings = Settings(database_url=DATABASE_URL, ingest_token_sha256=hashlib.sha256(TOKEN.encode()).hexdigest())
    config = uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning")
    srv = uvicorn.Server(config)
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    thread.join(timeout=5)


def hf_item(pid, title, upvotes, keywords, github=None):
    return {"paper": {"id": pid, "title": title, "summary": f"{title}. We show results.", "upvotes": upvotes,
                      "authors": [{"name": "Kim"}], "publishedAt": "2026-11-12T00:00:00.000Z",
                      "ai_summary": f"Summary of {title}.", "ai_keywords": keywords, "githubRepo": github}}


def fake_hf(day_items: dict[str, list], pages: dict[str, str] | None = None):
    pages = pages or {}

    def handler(request: httpx.Request):
        params = dict(request.url.params)
        if request.url.path in pages:
            return httpx.Response(200, text=pages[request.url.path])
        if request.url.path == "/api/daily_papers":
            items = day_items.get(params["date"], [])
            p, limit = int(params.get("p", 0)), int(params["limit"])
            return httpx.Response(200, json=items[p * limit:(p + 1) * limit])
        if request.url.path == "/api/models":
            return httpx.Response(200, json=[{"id": "Qwen/Qwen3.8-Flash-Next", "likes": 4502, "trendingScore": 4286,
                                              "pipeline_tag": "image-text-to-text"}])
        if request.url.path in ("/api/datasets", "/api/spaces"):
            return httpx.Response(200, json=[{"id": "org/item", "likes": 3, "trendingScore": 2}])
        return httpx.Response(404)

    return HFClient(httpx.Client(transport=httpx.MockTransport(handler), base_url="https://huggingface.co"),
                    sleep=lambda s: None)


def test_pipeline_uploads_and_app_api_reads(server, tmp_path, monkeypatch):
    monkeypatch.setenv("RADAR_IT_TOKEN", TOKEN)
    items = [hf_item(f"2611.{i:05d}", f"Agent memory study {i}", 40 - i, ["Agent", "Memory"]) for i in range(12)]
    items.append(hf_item("2611.99999", "Fast speech synthesis", 90, ["TTS"], github="https://github.com/a/b"))
    config = Config(
        server=ServerConfig(url=server, token_env="RADAR_IT_TOKEN"),
        ai=AIConfig(provider="none"),
        collect=CollectConfig(models=1, datasets=1, spaces=1),
        select=SelectConfig(max_featured=3, focus_topics=["agents"]),
        paths=PathsConfig(data_dir=str(tmp_path / "data")),
    )
    runner = Runner(
        config=config,
        hf=fake_hf({"2026-11-16": items}),
        server=ServerClient(httpx.Client(base_url=server), token=TOKEN, sleep=lambda s: None),
        analyzer=Analyzer(provider=None, max_ai_papers=60),
        now=lambda: dt.datetime(2026, 11, 17, 3, 0, tzinfo=dt.UTC),
        sleep=lambda s: None,
    )
    assert runner.run_daily() == EXIT_OK

    with httpx.Client(base_url=server) as app:
        digest = app.get("/api/v1/digests/latest").json()
        assert digest["date"] == "2026-11-16"
        assert len(digest["papers"]) == 13
        featured = [p["id"] for p in digest["papers"] if p["featured"]]
        assert featured[0] == "2611.99999"  # 서버 정렬: 주목 → 추천 수
        assert len(featured) == 3
        assert digest["headline"][0].startswith("Fast speech synthesis")
        assert digest["hub"][0]["id"] == "Qwen/Qwen3.8-Flash-Next"
        assert digest["hub"][0]["url"] == "https://huggingface.co/Qwen/Qwen3.8-Flash-Next"

        detail = app.get("/api/v1/papers/2611.00003").json()
        assert detail["paper"]["keywords"] == ["agent", "memory"]
        assert len(detail["related"]) == 5

        search = app.get("/api/v1/papers", params={"q": "memory", "featured": "true"}).json()
        assert search["total"] == 2

        week = app.get("/api/v1/trends/weekly/latest").json()
        assert week["key"] == "2026-W47" and week["paper_count"] == 13
        assert {t["topic"] for t in week["topics"]} >= {"agents", "speech-audio"}

        # 앱이 기대하는 키가 모두 있는지 (contract/samples 와 같은 모양)
        sample = json.loads((__import__("pathlib").Path(__file__).parents[1] / "contract/samples/digest_latest.json")
                            .read_text("utf-8"))
        assert set(sample) == set(digest)
        assert set(sample["papers"][0]) == set(digest["papers"][0])
        assert set(sample["hub"][0]) == set(digest["hub"][0])

    # 같은 날짜 재실행 (--date) 은 덮어쓰기 (멱등)
    assert runner.run_daily(explicit=dt.date(2026, 11, 16)) == EXIT_OK
    with httpx.Client(base_url=server) as app:
        assert len(app.get("/api/v1/digests/2026-11-16").json()["papers"]) == 13
        assert app.get("/api/v1/digests").json()["items"][0]["paper_count"] == 13


def test_wrong_token_is_rejected_end_to_end(server, tmp_path):
    client = ServerClient(httpx.Client(base_url=server), token="wrong", sleep=lambda s: None)
    from radar.models import DigestPayload
    from radar.publish import UploadError

    with pytest.raises(UploadError) as exc:
        client.upload_digest(DigestPayload(date=dt.date(2026, 11, 16), provider="none", papers=[], hub=[]))
    assert exc.value.status == 401


def test_backfill_fills_real_server(server, tmp_path, monkeypatch):
    # 백필 → 실제 서버: 날짜 목록 · 트렌드 · 리포트가 앱 API 로 보인다
    monkeypatch.setenv("RADAR_IT_TOKEN", TOKEN)
    days = {f"2026-11-{d:02d}": [hf_item(f"2611.{d:02d}{i:03d}", f"Agent memory paper {d}-{i}", i, ["Agent"])
                                 for i in range(4)] for d in range(2, 17)}
    config = Config(
        server=ServerConfig(url=server, token_env="RADAR_IT_TOKEN"),
        ai=AIConfig(provider="none"),
        collect=CollectConfig(models=1, datasets=1, spaces=1),
        paths=PathsConfig(data_dir=str(tmp_path / "bf")),
    )
    runner = Runner(
        config=config,
        hf=fake_hf(days),
        server=ServerClient(httpx.Client(base_url=server), token=TOKEN, sleep=lambda s: None),
        analyzer=Analyzer(provider=None, max_ai_papers=60),
        now=lambda: dt.datetime(2026, 11, 17, 3, 0, tzinfo=dt.UTC),
        sleep=lambda s: None,
    )
    assert runner.run_backfill(days=15) == EXIT_OK
    with httpx.Client(base_url=server) as app:
        items = app.get("/api/v1/digests?limit=90").json()["items"]
        assert len(items) == 15 and items[0]["date"] == "2026-11-16" and items[-1]["date"] == "2026-11-02"
        assert app.get("/api/v1/trends/periods").json()["weeks"] == ["2026-W47", "2026-W46", "2026-W45"]
        week = app.get("/api/v1/trends/weekly/2026-W46").json()
        assert week["paper_count"] == 28 and week["narrative"]
        latest = app.get("/api/v1/digests/latest").json()
        assert latest["hub"] and not app.get("/api/v1/digests/2026-11-10").json()["hub"]


FEED = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>llama.cpp v1</title><pubDate>Fri, 13 Nov 2026 14:05:22 GMT</pubDate>
<link>https://huggingface.co/blog/ggml-org/llama-cpp-v1</link></item>
<item><title>Old</title><pubDate>Fri, 26 Sep 2025 00:00:00 GMT</pubDate><link>https://huggingface.co/blog/old</link></item>
</channel></rss>"""
ARTICLE = (
    '<html><body><nav><p>menu</p></nav><div class="blog-content"><h1>llama.cpp v1</h1>'
    "<p>llama.cpp makes it possible to run multi-modal LLMs across a wide range of hardware.</p>"
    "<h2>Releases</h2><p>Signed binaries.</p></div></body></html>"
)


def test_news_and_original_text_end_to_end(server, tmp_path, monkeypatch):
    # FR-25 ~ FR-27: 뉴스 원문 · 논문 본문 원문 · HF 원본이 실제 서버 (Postgres) 에 저장되고 앱 API 로 보인다
    monkeypatch.setenv("RADAR_IT_TOKEN", TOKEN)
    items = [hf_item("2611.00001", "Agent memory study", 50, ["Agent"])]
    pages = {
        "/blog/feed.xml": FEED,
        "/blog/ggml-org/llama-cpp-v1": ARTICLE,
        "/papers/2611.00001.md": "# Agent memory study\n\nFull body.",
    }
    config = Config(
        server=ServerConfig(url=server, token_env="RADAR_IT_TOKEN"),
        ai=AIConfig(provider="none"),
        collect=CollectConfig(models=1, datasets=1, spaces=1, news_days=7),
        select=SelectConfig(max_featured=1),
        paths=PathsConfig(data_dir=str(tmp_path / "n")),
    )
    runner = Runner(
        config=config,
        hf=fake_hf({"2026-11-16": items}, pages),
        server=ServerClient(httpx.Client(base_url=server), token=TOKEN, sleep=lambda s: None),
        analyzer=Analyzer(provider=None, max_ai_papers=60),
        now=lambda: dt.datetime(2026, 11, 17, 3, 0, tzinfo=dt.UTC),
        sleep=lambda s: None,
    )
    assert runner.run_daily() == EXIT_OK
    with httpx.Client(base_url=server) as app:
        news = app.get("/api/v1/news").json()
        assert news["total"] == 1 and news["items"][0]["id"] == "ggml-org/llama-cpp-v1"
        detail = app.get("/api/v1/news/ggml-org/llama-cpp-v1").json()
        assert detail["content"].startswith("## llama.cpp v1") and "menu" not in detail["content"]
        assert detail["summary"].startswith("llama.cpp makes it possible")
        paper = app.get("/api/v1/papers/2611.00001").json()["paper"]
        assert paper["full_text"] == "# Agent memory study\n\nFull body." and paper["has_full_text"]
        for name in ("news_list.json", "news_detail.json"):
            sample = json.loads((__import__("pathlib").Path(__file__).parents[1] / "contract/samples" / name)
                                .read_text("utf-8"))
            got = news if name == "news_list.json" else detail
            assert set(sample) == set(got)
    with psycopg.connect(DATABASE_URL) as conn:
        assert conn.execute("select source_raw->'paper'->>'id' from papers").fetchone()[0] == "2611.00001"
        assert conn.execute("select source_raw->>'title' from news").fetchone()[0] == "llama.cpp v1"
