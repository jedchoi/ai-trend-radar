import hashlib

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TOKEN = "test-token-0123456789abcdef0123456789abcdef"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def make_paper(pid: str, **overrides) -> dict:
    paper = {
        "id": pid,
        "title": f"Paper {pid}",
        "authors": ["Kim", "Lee"],
        "abstract": f"Abstract of {pid}.",
        "upvotes": 10,
        "topic": "llm-reasoning",
        "keywords": ["reasoning"],
        "one_liner": f"{pid} 한 줄 요약",
        "featured": False,
        "summary_source": "hf",
    }
    paper.update(overrides)
    return paper


def make_hub(kind: str, rank: int, item_id: str, **overrides) -> dict:
    item = {"kind": kind, "rank": rank, "id": item_id, "likes": 100, "trending_score": 50.0}
    item.update(overrides)
    return item


def make_digest(date: str, papers=None, hub=None, headline=None, provider="none") -> dict:
    return {
        "date": date,
        "headline": headline if headline is not None else ["첫째 줄", "둘째 줄", "셋째 줄"],
        "provider": provider,
        "papers": papers if papers is not None else [],
        "hub": hub if hub is not None else [],
    }


@pytest.fixture
def settings(tmp_path):
    return Settings(
        db_path=str(tmp_path / "radar.db"),
        ingest_token_sha256=hashlib.sha256(TOKEN.encode()).hexdigest(),
        enable_docs=False,
        public_rate_per_min=1000,
        ingest_rate_per_min=1000,
    )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture
def ingest(client):
    def _ingest(payload: dict):
        resp = client.post("/api/v1/ingest/daily", json=payload, headers=AUTH)
        assert resp.status_code == 200, resp.text
        return resp.json()

    return _ingest
