"""PostgreSQL 저장소 고유 동작: 데이터베이스 자동 생성 · 연결 수명 · 검색어 정리."""

import datetime as dt
import uuid

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from app.repository import Repository, ensure_database, like_pattern, search_words
from tests.conftest import make_digest, make_paper


def test_missing_database_is_created(database_url):
    # 기존 Postgres 를 재사용할 때: 대상 데이터베이스가 없으면 만든다
    name = f"radar_tmp_{uuid.uuid4().hex[:8]}"
    url = make_conninfo(database_url, dbname=name)
    admin = make_conninfo(database_url, dbname="postgres")
    try:
        repo = Repository(url)
        repo.init(wait_s=3)
        assert repo.latest_date() is None
        repo.close()
        ensure_database(url)  # 이미 있으면 아무 일도 없음
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{name}"')


def test_repository_requires_init(database_url):
    repo = Repository(database_url)
    with pytest.raises(RuntimeError):
        repo.latest_date()
    repo.close()  # 열리지 않은 풀을 닫아도 안전


def test_reset_clears_everything(clean_db, ingest):
    ingest(make_digest("2026-11-13", [make_paper("2611.00001")]))
    repo = Repository(clean_db)
    repo.init()
    try:
        assert repo.paper_count(dt.date(2026, 11, 1), dt.date(2026, 11, 30)) == 1
        repo.reset()
        assert repo.latest_date() is None
    finally:
        repo.close()


def test_unreachable_server_raises_after_wait():
    repo = Repository("postgresql://radar@127.0.0.1:1/radar")
    with pytest.raises(psycopg.OperationalError):
        repo.init(wait_s=0)


def test_search_words_strip_symbols_and_escape_like():
    assert search_words("Agent* MoE! (RAG)") == ["agent", "moe", "rag"]
    assert search_words(None) == []
    assert like_pattern("a_b%c\\") == "%a\\_b\\%c\\\\%"
