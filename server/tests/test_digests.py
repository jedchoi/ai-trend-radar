from tests.conftest import make_digest, make_hub, make_paper


def test_latest_digest_has_headline_first(client, ingest):
    # AC-01-1: 최신 날짜 일일 요약 + 세 줄
    ingest(make_digest("2026-11-12", [make_paper("2611.00001")]))
    ingest(make_digest("2026-11-13", [make_paper("2611.00002")], headline=["a", "b", "c"]))
    resp = client.get("/api/v1/digests/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == "2026-11-13"
    assert body["headline"] == ["a", "b", "c"]


def test_latest_without_data_is_404(client):
    # BR-S22: 데이터 없음 → 404 + error 코드
    resp = client.get("/api/v1/digests/latest")
    assert resp.status_code == 404
    assert resp.json() == {"error": "not_found"}


def test_featured_first_then_upvotes_then_id(client, ingest):
    # BR-S06 / AC-01-2: 주목 먼저 → 추천 수 내림차순 → id 오름차순
    papers = [
        make_paper("2611.00001", upvotes=50),
        make_paper("2611.00002", upvotes=5, featured=True),
        make_paper("2611.00003", upvotes=20, featured=True),
        make_paper("2611.00004", upvotes=50),
    ]
    ingest(make_digest("2026-11-13", papers))
    ids = [p["id"] for p in client.get("/api/v1/digests/2026-11-13").json()["papers"]]
    assert ids == ["2611.00003", "2611.00002", "2611.00001", "2611.00004"]


def test_paper_fields_in_digest(client, ingest):
    # AC-01-2, AC-02-2, AC-06-1: 카드 필드 + 원문 링크
    paper = make_paper(
        "2611.00001",
        github_url="https://github.com/a/b",
        github_stars=12,
        upvotes=7,
        topic="agents",
        featured=True,
        detail={"what": "w", "novelty": "n", "why": "y", "apply": "a"},
    )
    ingest(make_digest("2026-11-13", [paper]))
    got = client.get("/api/v1/digests/2026-11-13").json()["papers"][0]
    assert got["topic"] == "agents"
    assert got["one_liner"] == "2611.00001 한 줄 요약"
    assert got["upvotes"] == 7
    assert got["github_url"] == "https://github.com/a/b"
    assert got["hf_url"] == "https://huggingface.co/papers/2611.00001"
    assert got["detail"]["apply"] == "a"


def test_digest_list_newest_first_with_limit(client, ingest):
    # BR-S05 / AC-01-3: 최신순, limit
    for day in ("2026-11-10", "2026-11-12", "2026-11-11"):
        ingest(make_digest(day, [make_paper(f"2611.1{day[-2:]}", featured=True)]))
    body = client.get("/api/v1/digests?limit=2").json()
    assert [i["date"] for i in body["items"]] == ["2026-11-12", "2026-11-11"]
    assert body["items"][0]["paper_count"] == 1
    assert body["items"][0]["featured_count"] == 1


def test_digest_list_limit_out_of_range_is_422(client):
    # BR-S05: limit 1~90
    assert client.get("/api/v1/digests?limit=0").status_code == 422
    assert client.get("/api/v1/digests?limit=91").status_code == 422


def test_bad_date_path_is_422(client):
    # BR-S22: 형식이 틀린 날짜
    assert client.get("/api/v1/digests/2026-13-45").status_code == 422


def test_hub_items_by_kind_with_url(client, ingest):
    # AC-03-1, AC-03-3: 종류 · 순위 · 좋아요 · 페이지 주소
    hub = [make_hub("model", 1, "org/m1", likes=10), make_hub("dataset", 1, "org/d1"), make_hub("space", 1, "org/s1")]
    ingest(make_digest("2026-11-13", hub=hub))
    items = client.get("/api/v1/digests/2026-11-13").json()["hub"]
    urls = {i["id"]: i["url"] for i in items}
    assert urls == {
        "org/m1": "https://huggingface.co/org/m1",
        "org/d1": "https://huggingface.co/datasets/org/d1",
        "org/s1": "https://huggingface.co/spaces/org/s1",
    }


def test_hub_is_new_against_previous_day(client, ingest):
    # BR-S07 / AC-03-2: 전날 목록에 없던 항목만 신규
    ingest(make_digest("2026-11-12", hub=[make_hub("model", 1, "org/old")]))
    ingest(make_digest("2026-11-13", hub=[make_hub("model", 1, "org/old"), make_hub("model", 2, "org/new")]))
    items = {i["id"]: i for i in client.get("/api/v1/digests/2026-11-13").json()["hub"]}
    assert items["org/old"]["is_new"] is False
    assert items["org/new"]["is_new"] is True


def test_hub_is_new_false_when_previous_day_missing(client, ingest):
    # BR-S07: 전날 Hub 데이터가 없으면 false
    ingest(make_digest("2026-11-10", hub=[make_hub("model", 1, "org/a")]))
    ingest(make_digest("2026-11-13", hub=[make_hub("model", 1, "org/b")]))
    items = client.get("/api/v1/digests/2026-11-13").json()["hub"]
    assert items[0]["is_new"] is False


def test_hub_streak_counts_consecutive_days(client, ingest):
    # BR-S08: 연속 일수 (그날 포함)
    ingest(make_digest("2026-11-10", hub=[make_hub("model", 1, "org/a")]))
    ingest(make_digest("2026-11-11", hub=[make_hub("model", 1, "org/a")]))
    ingest(make_digest("2026-11-12", hub=[make_hub("model", 1, "org/a")]))
    ingest(make_digest("2026-11-13", hub=[make_hub("model", 1, "org/a"), make_hub("model", 2, "org/b")]))
    items = {i["id"]: i for i in client.get("/api/v1/digests/2026-11-13").json()["hub"]}
    assert items["org/a"]["streak_days"] == 4
    assert items["org/b"]["streak_days"] == 1


def test_hub_sorted_by_kind_then_rank(client, ingest):
    # AC-03-1: 종류별 순위
    hub = [
        make_hub("space", 1, "o/s"),
        make_hub("model", 2, "o/m2"),
        make_hub("model", 1, "o/m1"),
        make_hub("dataset", 1, "o/d"),
    ]
    ingest(make_digest("2026-11-13", hub=hub))
    ids = [i["id"] for i in client.get("/api/v1/digests/2026-11-13").json()["hub"]]
    assert ids == ["o/m1", "o/m2", "o/d", "o/s"]


def test_health_reports_latest_date(client, ingest):
    # 운영: health
    assert client.get("/api/v1/health").json() == {"status": "ok", "latest_date": None}
    ingest(make_digest("2026-11-13"))
    assert client.get("/api/v1/health").json()["latest_date"] == "2026-11-13"
