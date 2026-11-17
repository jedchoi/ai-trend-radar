"""통합 테스트 (Build and Test): PC 파이프라인 → 실제 HTTP → backend 서버 → 앱이 읽는 API.

실행: PYTHONPATH=server:pipeline pytest integration -q
Hugging Face 는 가짜 응답 (MockTransport), 서버는 uvicorn 으로 실제 포트에서 띄운다.
"""

import datetime as dt
import hashlib
import json
import socket
import threading
import time

import httpx
import pytest
import uvicorn

from app.config import Settings
from app.main import create_app
from radar.analyze import Analyzer
from radar.config import AIConfig, CollectConfig, Config, PathsConfig, SelectConfig, ServerConfig
from radar.hf_client import HFClient
from radar.publish import ServerClient
from radar.runner import EXIT_OK, Runner

TOKEN = "integration-token-0123456789abcdef"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server(tmp_path):
    port = free_port()
    settings = Settings(db_path=str(tmp_path / "it.db"), ingest_token_sha256=hashlib.sha256(TOKEN.encode()).hexdigest())
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


def fake_hf(day_items: dict[str, list]):
    def handler(request: httpx.Request):
        params = dict(request.url.params)
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
