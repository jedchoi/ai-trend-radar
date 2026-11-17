import hashlib
import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repository import TABLES, Repository

# 테스트 전용 데이터베이스. 없으면 만든다 (tool/test-db.sh 가 도커로 띄우는 기본 주소)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://radar@127.0.0.1:55432/radar_test")

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


@pytest.fixture(scope="session")
def database_url() -> str:
    repo = Repository(TEST_DATABASE_URL)
    try:
        repo.init(wait_s=3)
    except psycopg.OperationalError as exc:
        pytest.exit(f"PostgreSQL 접속 실패 ({exc}). tool/test-db.sh 를 실행하거나 TEST_DATABASE_URL 을 지정하세요.")
    repo.close()
    return TEST_DATABASE_URL


@pytest.fixture
def clean_db(database_url) -> str:
    """테스트마다 빈 데이터베이스."""
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY")
    return database_url


@pytest.fixture
def settings(clean_db):
    return Settings(
        database_url=clean_db,
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
