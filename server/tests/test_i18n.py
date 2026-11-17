"""두 언어 응답 (4주기, FR-38 ~ FR-42): BR-S41 ~ BR-S43, BR-S50, BR-S51."""

import psycopg

from tests.conftest import AUTH, make_digest, make_paper
from tests.test_news import make_news, upload

URL = "/api/v1/ingest/translations"
DETAIL_KO = {"what": "무엇", "novelty": "새로움", "why": "중요", "apply": "적용"}
DETAIL_EN = {"what": "What", "novelty": "New", "why": "Why", "apply": "Apply"}


def tr(kind, key, lang, **fields):
    return {"kind": kind, "key": key, "lang": lang, "fields": fields}


def send(client, *items, provider="claude"):
    return client.post(URL, json={"provider": provider, "items": list(items)}, headers=AUTH)


def seed(client, ingest):
    ko_paper = make_paper(
        "2611.00001",
        title="Agent Memory",
        abstract="We study memory.",
        one_liner="에이전트 기억 연구",
        featured=True,
        detail=DETAIL_KO,
        glossary=[{"term": "기억", "explanation": "설명"}],
        full_text="# Intro\n\nBody text.",
        keywords=["memory"],
        summary_source="ai",
    )
    # AI 없이 만든 요약 (Hugging Face 영어 요약) → 기준 언어 en
    en_paper = make_paper("2611.00002", title="Other", one_liner="An English summary.", summary_source="hf")
    ingest(make_digest("2026-11-13", [ko_paper, en_paper], headline=["첫째", "둘째"]))
    upload(client, [make_news("ggml-org/llama-cpp-v1", title="llama.cpp v1", content="Original body.")])
    body = {"period": "week", "key": "2026-W46", "narrative": "이번 주 리포트"}
    assert client.post("/api/v1/ingest/report", json=body, headers=AUTH).status_code == 200


def seed_translations(client):
    resp = send(
        client,
        tr(
            "paper",
            "2611.00001",
            "en",
            one_liner="A study of agent memory",
            detail=DETAIL_EN,
            glossary=[{"term": "memory", "explanation": "explained"}],
        ),
        tr("paper", "2611.00002", "ko", one_liner="영어 요약을 옮긴 문장"),
        tr("digest", "2026-11-13", "en", headline=["First", "Second"]),
        tr("news", "ggml-org/llama-cpp-v1", "en", summary="English summary", key_points=["Point"]),
        tr("report", "week:2026-W46", "en", narrative="This week's report"),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"translations": 5}


def test_upload_requires_token_and_summary_fields_only(client):
    # BR-S01, BR-S41, FR-41: 원문 (제목 · 초록 · 본문) 은 번역 필드가 아니다
    item = tr("paper", "2611.00001", "en", one_liner="x")
    assert client.post(URL, json={"items": [item]}).status_code == 401
    assert send(client, tr("paper", "bad id!", "en", one_liner="x")).status_code == 422
    assert send(client, tr("paper", "2611.00001", "fr", one_liner="x")).status_code == 422
    for field in ("title", "abstract", "full_text"):
        assert send(client, tr("paper", "2611.00001", "ko", **{field: "x"})).status_code == 422
    for field in ("title", "content"):
        assert send(client, tr("news", "a/b", "ko", **{field: "x"})).status_code == 422
    assert send(client, tr("paper", "2611.00001", "ko")).status_code == 422  # 빈 필드
    assert send(client, tr("digest", "2026-13-01", "en", headline=["x"])).status_code == 422
    assert send(client, tr("report", "2026-W46", "en", narrative="x")).status_code == 422  # week: 접두 필요
    assert send(client, *[tr("paper", f"2611.{i:05d}", "en", one_liner="t") for i in range(51)]).status_code == 422
    assert send(client, item).status_code == 200


def test_fields_are_merged_and_logged(client, settings):
    send(client, tr("news", "a/b", "en", summary="S", key_points=["P"]))
    send(client, tr("news", "a/b", "en", summary="S2"))
    with psycopg.connect(settings.database_url) as conn:
        assert conn.execute("select fields from translations").fetchone()[0] == {"summary": "S2", "key_points": ["P"]}
        assert conn.execute("select count(*) from ingest_log where kind = 'translation'").fetchone()[0] == 2


def test_digest_has_both_languages_in_one_response(client, ingest):
    # FR-39, BR-S50, AC-32-2
    seed(client, ingest)
    seed_translations(client)
    digest = client.get("/api/v1/digests/latest").json()
    assert digest["i18n"] == {"ko": {"headline": ["첫째", "둘째"]}, "en": {"headline": ["First", "Second"]}}
    p1 = next(p for p in digest["papers"] if p["id"] == "2611.00001")
    assert p1["i18n"]["ko"] == {
        "one_liner": "에이전트 기억 연구",
        "detail": DETAIL_KO,
        "glossary": [{"term": "기억", "explanation": "설명"}],
    }
    assert p1["i18n"]["en"]["one_liner"] == "A study of agent memory" and p1["i18n"]["en"]["detail"] == DETAIL_EN
    p2 = next(p for p in digest["papers"] if p["id"] == "2611.00002")
    assert p2["i18n"] == {"en": {"one_liner": "An English summary."}, "ko": {"one_liner": "영어 요약을 옮긴 문장"}}
    # FR-41: 원문은 언제나 원래 값 (영어), i18n 에 없음
    assert p1["title"] == "Agent Memory" and p1["abstract"] == "We study memory."
    assert "title" not in p1["i18n"]["en"] and "abstract" not in p1["i18n"]["ko"]
    # 기존 단일 필드는 원래 값 그대로 (이전 앱 호환)
    assert p1["one_liner"] == "에이전트 기억 연구" and digest["headline"] == ["첫째", "둘째"]
    items = client.get("/api/v1/digests").json()["items"]
    assert items[0]["i18n"]["en"]["headline"] == ["First", "Second"]


def test_missing_translation_gives_one_language(client, ingest):
    # AC-32-3: 번역 전에는 기준 언어 하나만
    seed(client, ingest)
    digest = client.get("/api/v1/digests/latest").json()
    assert digest["i18n"] == {"ko": {"headline": ["첫째", "둘째"]}}
    p2 = next(p for p in digest["papers"] if p["id"] == "2611.00002")
    assert p2["i18n"] == {"en": {"one_liner": "An English summary."}}


def test_base_value_wins_over_same_language_translation(client, ingest):
    # BR-S50: AI 재분석으로 기준 언어가 바뀌어도 (영어 → 한국어) 옛 번역이 새 원래 값을 덮지 않는다
    seed(client, ingest)
    send(client, tr("paper", "2611.00002", "ko", one_liner="옛 번역"))
    ingest(make_digest("2026-11-13", [make_paper("2611.00002", one_liner="새 한국어 요약", summary_source="ai")]))
    paper = client.get("/api/v1/papers/2611.00002").json()["paper"]
    assert paper["i18n"] == {"ko": {"one_liner": "새 한국어 요약"}}


def test_paper_detail_related_search_news_and_report(client, ingest):
    seed(client, ingest)
    seed_translations(client)
    data = client.get("/api/v1/papers/2611.00001").json()
    assert data["paper"]["i18n"]["en"]["one_liner"] == "A study of agent memory"
    assert data["paper"]["full_text"] == "# Intro\n\nBody text."
    found = client.get("/api/v1/papers?q=memory").json()["items"]
    assert found[0]["i18n"]["en"]["one_liner"] == "A study of agent memory"
    news = client.get("/api/v1/news").json()["items"][0]
    assert news["i18n"]["en"] == {"summary": "English summary"} and news["title"] == "llama.cpp v1"
    detail = client.get("/api/v1/news/ggml-org/llama-cpp-v1").json()
    assert detail["i18n"]["en"] == {"summary": "English summary", "key_points": ["Point"]}
    assert detail["i18n"]["ko"]["key_points"] == ["핵심 1", "핵심 2"] and detail["content"] == "Original body."
    week = client.get("/api/v1/trends/weekly/2026-W46").json()
    assert week["i18n"] == {"ko": {"narrative": "이번 주 리포트"}, "en": {"narrative": "This week's report"}}
    assert "i18n" in week["top_papers"][0]


def test_search_finds_by_translated_summary(client, ingest):
    # FR-37: 번역된 요약 낱말로도 찾는다
    seed(client, ingest)
    seed_translations(client)
    assert client.get("/api/v1/papers?q=옮긴").json()["total"] == 1
    assert client.get("/api/v1/news?q=english%20summary").json()["total"] == 1


def test_translations_survive_reupload(client, ingest):
    # BR-S42, BR-S43
    seed(client, ingest)
    seed_translations(client)
    ingest(make_digest("2026-11-13", [make_paper("2611.00002", title="Other", one_liner="An English summary.")]))
    assert client.get("/api/v1/papers/2611.00002").json()["paper"]["i18n"]["ko"]["one_liner"] == "영어 요약을 옮긴 문장"
    assert client.get("/api/v1/papers?q=옮긴").json()["total"] == 1
    upload(client, [make_news("ggml-org/llama-cpp-v1", title="llama.cpp v1", content="Original body v2.")])
    assert client.get("/api/v1/news?q=english%20summary").json()["total"] == 1
