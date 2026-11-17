"""논문 원문 (FR-26, FR-27): BR-S31, BR-S32."""

import psycopg

from tests.conftest import make_digest, make_paper


def test_full_text_only_in_paper_detail(client, ingest):
    # BR-S32, AC-23-1
    paper = make_paper("2611.00001", featured=True, full_text="Introduction. " * 1000)
    ingest(make_digest("2026-11-13", [paper, make_paper("2611.00002")]))
    detail = client.get("/api/v1/papers/2611.00001").json()["paper"]
    assert detail["full_text"].startswith("Introduction.")
    assert detail["has_full_text"] is True
    assert detail["arxiv_url"] == "https://arxiv.org/abs/2611.00001"
    digest = client.get("/api/v1/digests/2026-11-13").json()
    by_id = {p["id"]: p for p in digest["papers"]}
    assert by_id["2611.00001"]["full_text"] is None
    assert by_id["2611.00001"]["has_full_text"] is True
    assert by_id["2611.00002"]["has_full_text"] is False


def test_source_raw_is_stored_not_exposed(client, ingest, settings):
    # BR-S31
    raw = {"paper": {"id": "2611.00001", "ai_summary": "x"}, "numComments": 3}
    ingest(make_digest("2026-11-13", [make_paper("2611.00001", source_raw=raw)]))
    detail = client.get("/api/v1/papers/2611.00001").json()["paper"]
    assert "source_raw" not in detail
    assert "source_raw" not in client.get("/api/v1/digests/latest").json()["papers"][0]
    with psycopg.connect(settings.database_url) as conn:
        assert conn.execute("select source_raw from papers").fetchone()[0] == raw


def test_full_text_limit(client):
    # NFR-11: 원문 최대 200,000자
    from tests.conftest import AUTH

    payload = make_digest("2026-11-13", [make_paper("2611.00001", full_text="x" * 200_001)])
    assert client.post("/api/v1/ingest/daily", json=payload, headers=AUTH).status_code == 422
