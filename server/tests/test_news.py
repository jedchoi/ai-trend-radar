"""뉴스 (FR-25, FR-27): BR-S30 ~ BR-S34."""

import psycopg

from tests.conftest import AUTH

URL = "/api/v1/ingest/news"


def make_news(nid: str, **overrides) -> dict:
    news = {
        "id": nid,
        "url": f"https://huggingface.co/blog/{nid}",
        "title": f"News {nid}",
        "published_at": "2026-11-13T18:00:39Z",
        "organization": nid.split("/")[0] if "/" in nid else None,
        "authors": ["Kim"],
        "content": f"Original body of {nid}. It has many words.",
        "summary": f"{nid} 한국어 요약",
        "key_points": ["핵심 1", "핵심 2"],
        "keywords": ["inference"],
        "topic": "training-optimization",
        "summary_source": "ai",
    }
    news.update(overrides)
    return news


def upload(client, items, provider="claude"):
    return client.post(URL, json={"provider": provider, "items": items}, headers=AUTH)


def test_news_requires_token(client):
    # BR-S01
    assert client.post(URL, json={"items": [make_news("a/b")]}).status_code == 401


def test_upload_and_detail_keeps_original_text(client):
    # BR-S30, AC-22-2: 원문 본문 전체 저장
    body = "x" * 150_000
    resp = upload(client, [make_news("ggml-org/llama-cpp-v1", content=body)])
    assert resp.status_code == 200
    assert resp.json() == {"news": 1}
    news = client.get("/api/v1/news/ggml-org/llama-cpp-v1").json()
    assert news["content"] == body
    assert news["key_points"] == ["핵심 1", "핵심 2"]
    assert news["organization"] == "ggml-org"
    assert "source_raw" not in news
    assert client.get("/api/v1/news/nope/nope").status_code == 404


def test_same_id_is_overwritten(client):
    # BR-S30: 같은 id 는 덮어쓰기
    upload(client, [make_news("a/one", title="old")])
    upload(client, [make_news("a/one", title="new")])
    body = client.get("/api/v1/news").json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "new"


def test_list_newest_first_with_paging(client):
    # AC-22-1
    items = [make_news(f"org/n{i}", published_at=f"2026-11-{10 + i:02d}T00:00:00Z") for i in range(5)]
    upload(client, items)
    page = client.get("/api/v1/news?limit=2&offset=1").json()
    assert page["total"] == 5
    assert [n["id"] for n in page["items"]] == ["org/n3", "org/n2"]
    assert "content" not in page["items"][0]


def test_search_matches_title_summary_keywords_body(client):
    # BR-S33, AC-22-3
    upload(
        client,
        [
            make_news("a/one", title="Faster llama.cpp", content="quantization tricks"),
            make_news("a/two", title="Robots", keywords=["robotics"], topic="robotics-physical"),
            make_news("a/three", title="Other", summary="에이전트 소식"),
        ],
    )
    ids = lambda q: [n["id"] for n in client.get(f"/api/v1/news?q={q}").json()["items"]]  # noqa: E731
    assert ids("llama") == ["a/one"]
    assert ids("QUANTIZATION") == ["a/one"]
    assert ids("robotics") == ["a/two"]
    assert ids("에이전트") == ["a/three"]
    assert ids("faster%20tricks") == ["a/one"]
    topic = client.get("/api/v1/news?topic=robotics-physical").json()["items"]
    assert [n["id"] for n in topic] == ["a/two"]


def test_invalid_news_is_422(client):
    # BR-S04
    assert upload(client, [make_news("Bad Id!")]).status_code == 422
    assert upload(client, [make_news("a/b", summary="")]).status_code == 422
    assert upload(client, [make_news("a/b", content="x" * 200_001)]).status_code == 422
    assert upload(client, [make_news(f"a/{i}") for i in range(21)]).status_code == 422
    assert upload(client, [make_news("a/b"), make_news("a/b")]).status_code == 422


def test_news_is_logged_and_raw_kept(client, settings):
    # BR-S30, BR-S31: ingest_log 1행, 원본은 저장만
    upload(client, [make_news("a/b", source_raw={"guid": "x", "pubDate": "Fri"})])
    with psycopg.connect(settings.database_url) as conn:
        assert conn.execute("select kind, count from ingest_log").fetchall() == [("news", 1)]
        assert conn.execute("select source_raw from news").fetchone()[0] == {"guid": "x", "pubDate": "Fri"}


def test_large_upload_up_to_ten_megabytes(client):
    # BR-S34: 원문 여러 건 (약 3 MB) 업로드 허용
    items = [make_news(f"a/{i}", content="y" * 150_000) for i in range(20)]
    assert upload(client, items).status_code == 200
