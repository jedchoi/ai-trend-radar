from tests.conftest import make_digest, make_paper


def test_paper_detail_and_404(client, ingest):
    # AC-05-1, BR-S22
    ingest(make_digest("2026-11-13", [make_paper("2611.00001", glossary=[{"term": "MoE", "explanation": "x"}])]))
    body = client.get("/api/v1/papers/2611.00001").json()
    assert body["paper"]["glossary"] == [{"term": "MoE", "explanation": "x"}]
    assert client.get("/api/v1/papers/2611.99999").status_code == 404


def test_bad_paper_id_is_422(client):
    # 입력 검증: id 형식
    assert client.get("/api/v1/papers/a%20b").status_code == 422


def test_related_shares_keyword_and_is_not_newer(client, ingest):
    # BR-S09 / AC-07-1: 키워드 공유 · 같은 날짜 이하 · 자기 자신 제외 · 날짜 내림차순
    ingest(
        make_digest(
            "2026-11-10",
            [make_paper("2611.00001", keywords=["moe", "routing"]), make_paper("2611.00002", keywords=["diffusion"])],
        )
    )
    ingest(make_digest("2026-11-12", [make_paper("2611.00003", keywords=["MoE"])]))
    ingest(
        make_digest(
            "2026-11-13",
            [make_paper("2611.00004", keywords=["moe", "routing"]), make_paper("2611.00005", keywords=["routing"])],
        )
    )
    ingest(make_digest("2026-11-14", [make_paper("2611.00006", keywords=["moe"])]))
    related = client.get("/api/v1/papers/2611.00004").json()["related"]
    assert [r["id"] for r in related] == ["2611.00005", "2611.00003", "2611.00001"]


def test_related_order_within_same_date(client, ingest):
    # BR-S09: 같은 날짜면 공유 키워드 수 → 추천 수
    ingest(
        make_digest(
            "2026-11-10",
            [
                make_paper("2611.00001", keywords=["a"], upvotes=99),
                make_paper("2611.00002", keywords=["a", "b"], upvotes=1),
                make_paper("2611.00003", keywords=["a"], upvotes=50),
            ],
        )
    )
    ingest(make_digest("2026-11-11", [make_paper("2611.00009", keywords=["a", "b"])]))
    related = client.get("/api/v1/papers/2611.00009").json()["related"]
    assert [r["id"] for r in related] == ["2611.00002", "2611.00001", "2611.00003"]


def test_related_max_five(client, ingest):
    # BR-S09: 최대 5편
    ingest(make_digest("2026-11-10", [make_paper(f"2611.0000{i}", keywords=["k"]) for i in range(1, 9)]))
    assert len(client.get("/api/v1/papers/2611.00001").json()["related"]) == 5


def test_search_matches_title_summary_keywords_newest_first(client, ingest):
    # BR-S10 / AC-12-1
    ingest(make_digest("2026-11-10", [make_paper("2611.00001", title="Sparse Mixture of Experts")]))
    ingest(make_digest("2026-11-12", [make_paper("2611.00002", one_liner="전문가 혼합 mixture 라우팅")]))
    ingest(
        make_digest(
            "2026-11-13", [make_paper("2611.00003", keywords=["mixture"]), make_paper("2611.00004", title="Other")]
        )
    )
    body = client.get("/api/v1/papers", params={"q": "mixture"}).json()
    assert [i["id"] for i in body["items"]] == ["2611.00003", "2611.00002", "2611.00001"]
    assert body["total"] == 3


def test_search_is_prefix_and_all_words(client, ingest):
    # BR-S10: 접두어 일치, 모든 단어 AND
    ingest(
        make_digest(
            "2026-11-13",
            [
                make_paper("2611.00001", title="Agentic coding benchmark"),
                make_paper("2611.00002", title="Agentic robots"),
            ],
        )
    )
    ids = [i["id"] for i in client.get("/api/v1/papers", params={"q": "agent bench"}).json()["items"]]
    assert ids == ["2611.00001"]


def test_search_special_characters_are_safe(client, ingest):
    # BR-S10 / NFR-S06: FTS 문법 문자 정화
    ingest(make_digest("2026-11-13", [make_paper("2611.00001", title="Robust agents")]))
    for q in ['"', "agents OR", "a* NEAR(b)", "') ; drop table papers; --", "-", "^agents"]:
        resp = client.get("/api/v1/papers", params={"q": q})
        assert resp.status_code == 200, q
    assert client.get("/api/v1/papers/2611.00001").status_code == 200


def test_search_filters_topic_period_featured(client, ingest):
    # AC-12-2
    ingest(make_digest("2026-11-01", [make_paper("2611.00001", topic="agents", featured=True)]))
    ingest(
        make_digest(
            "2026-11-13",
            [
                make_paper("2611.00002", topic="agents"),
                make_paper("2611.00003", topic="agents", featured=True),
                make_paper("2611.00004", topic="speech-audio", featured=True),
            ],
        )
    )
    params = {"topic": "agents", "since": "2026-11-10", "featured": "true"}
    assert [i["id"] for i in client.get("/api/v1/papers", params=params).json()["items"]] == ["2611.00003"]
    params = {"until": "2026-11-05"}
    assert [i["id"] for i in client.get("/api/v1/papers", params=params).json()["items"]] == ["2611.00001"]


def test_search_no_results(client, ingest):
    # AC-12-3
    ingest(make_digest("2026-11-13", [make_paper("2611.00001")]))
    assert client.get("/api/v1/papers", params={"q": "zzzz"}).json() == {"items": [], "total": 0}


def test_search_paging_and_limits(client, ingest):
    # BR-S11: limit · offset · total
    ingest(make_digest("2026-11-13", [make_paper(f"2611.0000{i}", upvotes=i) for i in range(1, 8)]))
    body = client.get("/api/v1/papers", params={"limit": 3, "offset": 3}).json()
    assert [i["id"] for i in body["items"]] == ["2611.00004", "2611.00003", "2611.00002"]
    assert body["total"] == 7
    assert client.get("/api/v1/papers", params={"limit": 51}).status_code == 422
    assert client.get("/api/v1/papers", params={"q": "x" * 400}).status_code == 422


def test_search_too_many_words_uses_first_eight(client, ingest):
    # BR-S10: 단어 최대 8개
    ingest(make_digest("2026-11-13", [make_paper("2611.00001", title="a b c d e f g h")]))
    q = "a b c d e f g h zzz"
    assert client.get("/api/v1/papers", params={"q": q}).json()["total"] == 1
