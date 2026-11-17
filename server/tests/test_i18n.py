"""한국어 · 영어 (FR-32 ~ FR-37): BR-S40 ~ BR-S43."""

import psycopg

from tests.conftest import AUTH, make_digest, make_paper
from tests.test_news import make_news, upload

URL = "/api/v1/ingest/translations"


def tr(kind, key, lang, **fields):
    return {"kind": kind, "key": key, "lang": lang, "fields": fields}


def send(client, *items, provider="claude"):
    return client.post(URL, json={"provider": provider, "items": list(items)}, headers=AUTH)


DETAIL = {"what": "무엇", "novelty": "새로움", "why": "중요", "apply": "적용"}


def seed(client, ingest):
    paper = make_paper(
        "2611.00001",
        title="Agent Memory",
        abstract="We study memory.",
        one_liner="에이전트 기억 연구",
        featured=True,
        detail=DETAIL,
        glossary=[{"term": "기억", "explanation": "설명"}],
        full_text="# Intro\n\nBody text.",
        keywords=["memory"],
    )
    ingest(make_digest("2026-11-13", [paper, make_paper("2611.00002", title="Other")], headline=["첫째", "둘째"]))
    upload(client, [make_news("ggml-org/llama-cpp-v1", title="llama.cpp v1", content="Original body.")])
    body = {"period": "week", "key": "2026-W46", "narrative": "이번 주 리포트"}
    assert client.post("/api/v1/ingest/report", json=body, headers=AUTH).status_code == 200


def seed_translations(client):
    resp = send(
        client,
        tr(
            "paper", "2611.00001", "ko", title="에이전트 기억", abstract="기억을 연구한다.", full_text="# 소개\n\n본문."
        ),
        tr(
            "paper",
            "2611.00001",
            "en",
            one_liner="A study of agent memory",
            detail={"what": "What", "novelty": "New", "why": "Why", "apply": "Apply"},
            glossary=[{"term": "memory", "explanation": "explained"}],
        ),
        tr("digest", "2026-11-13", "en", headline=["First", "Second"]),
        tr("news", "ggml-org/llama-cpp-v1", "ko", title="라마 cpp 1.0", content="번역된 본문."),
        tr("news", "ggml-org/llama-cpp-v1", "en", summary="English summary", key_points=["Point"]),
        tr("report", "week:2026-W46", "en", narrative="This week's report"),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"translations": 6}


def test_translation_upload_requires_token_and_valid_shape(client):
    # BR-S01, BR-S41
    item = tr("paper", "2611.00001", "ko", title="제목")
    assert client.post(URL, json={"items": [item]}).status_code == 401
    assert send(client, tr("paper", "bad id!", "ko", title="x")).status_code == 422
    assert send(client, tr("paper", "2611.00001", "fr", title="x")).status_code == 422
    assert send(client, tr("paper", "2611.00001", "ko", headline=["x"])).status_code == 422  # 허용 키 아님
    assert send(client, tr("paper", "2611.00001", "ko")).status_code == 422  # 빈 필드
    assert send(client, tr("digest", "2026-13-01", "en", headline=["x"])).status_code == 422
    assert send(client, tr("report", "2026-W46", "en", narrative="x")).status_code == 422  # week: 접두 필요
    assert send(client, tr("news", "a/b", "ko", content="x" * 200_001)).status_code == 422
    assert send(client, *[tr("paper", f"2611.{i:05d}", "ko", title="t") for i in range(51)]).status_code == 422
    assert send(client, tr("paper", "2611.00001", "ko", title="제목")).status_code == 200


def test_fields_are_merged_and_logged(client, settings):
    # BR-S41: 키 단위로 합친다 (짧은 항목 먼저, 본문은 나중에)
    send(client, tr("paper", "2611.00001", "ko", title="제목", abstract="초록"))
    send(client, tr("paper", "2611.00001", "ko", full_text="본문"))
    send(client, tr("paper", "2611.00001", "ko", title="새 제목"))
    with psycopg.connect(settings.database_url) as conn:
        fields = conn.execute("select fields from translations").fetchone()[0]
        assert fields == {"title": "새 제목", "abstract": "초록", "full_text": "본문"}
        assert conn.execute("select count(*) from ingest_log where kind = 'translation'").fetchone()[0] == 3


def test_digest_in_english_and_korean(client, ingest):
    # BR-S40, AC-29-1, AC-29-2
    seed(client, ingest)
    seed_translations(client)
    en = client.get("/api/v1/digests/latest?lang=en").json()
    assert en["headline"] == ["First", "Second"] and en["untranslated"] is False
    p1 = next(p for p in en["papers"] if p["id"] == "2611.00001")
    assert p1["one_liner"] == "A study of agent memory"
    assert p1["detail"]["what"] == "What" and p1["glossary"][0]["term"] == "memory"
    assert p1["title"] == "Agent Memory"  # 영어 원문 그대로
    ko = client.get("/api/v1/digests/2026-11-13?lang=ko").json()
    p1 = next(p for p in ko["papers"] if p["id"] == "2611.00001")
    assert p1["title"] == "에이전트 기억" and p1["abstract"] == "기억을 연구한다."
    assert p1["full_text"] is None  # 목록에는 긴 필드 없음
    p2 = next(p for p in ko["papers"] if p["id"] == "2611.00002")
    assert p2["title"] == "Other" and p2["untranslated"] is True
    items = client.get("/api/v1/digests?lang=en").json()["items"]
    assert items[0]["headline"] == ["First", "Second"]


def test_no_lang_keeps_original_response(client, ingest):
    # FR-33: lang 이 없으면 지금과 같은 응답 (호환)
    seed(client, ingest)
    before = client.get("/api/v1/digests/latest").json()
    seed_translations(client)
    after = client.get("/api/v1/digests/latest").json()
    for doc in (before, after):
        doc.pop("untranslated", None)
        for p in doc["papers"]:
            p.pop("untranslated", None)
    assert before == after


def test_paper_detail_and_related_and_search(client, ingest):
    seed(client, ingest)
    seed_translations(client)
    ko = client.get("/api/v1/papers/2611.00001?lang=ko").json()["paper"]
    assert ko["full_text"] == "# 소개\n\n본문." and ko["title"] == "에이전트 기억"
    en = client.get("/api/v1/papers/2611.00001?lang=en").json()["paper"]
    assert en["full_text"] == "# Intro\n\nBody text."
    found = client.get("/api/v1/papers?q=에이전트&lang=ko").json()
    assert [p["id"] for p in found["items"]] == ["2611.00001"]
    assert found["items"][0]["title"] == "에이전트 기억"
    # FR-37: 번역 낱말로 찾기 (원문은 영어)
    assert client.get("/api/v1/papers?q=기억을").json()["total"] == 1


def test_news_list_and_detail(client, ingest):
    seed(client, ingest)
    seed_translations(client)
    ko = client.get("/api/v1/news?lang=ko").json()["items"][0]
    assert ko["title"] == "라마 cpp 1.0"
    detail = client.get("/api/v1/news/ggml-org/llama-cpp-v1?lang=ko").json()
    assert detail["content"] == "번역된 본문." and detail["untranslated"] is False
    en = client.get("/api/v1/news/ggml-org/llama-cpp-v1?lang=en").json()
    assert en["summary"] == "English summary" and en["key_points"] == ["Point"]
    assert en["content"] == "Original body."
    assert client.get("/api/v1/news?q=번역된").json()["total"] == 1


def test_trend_report_narrative(client, ingest):
    seed(client, ingest)
    seed_translations(client)
    week = client.get("/api/v1/trends/weekly/2026-W46?lang=en").json()
    assert week["narrative"] == "This week's report" and week["untranslated"] is False
    ko_week = client.get("/api/v1/trends/weekly/2026-W46?lang=ko").json()
    assert ko_week["narrative"] == "이번 주 리포트" and ko_week["untranslated"] is True
    assert ko_week["top_papers"][0]["title"] in ("에이전트 기억", "Other")
    assert client.get("/api/v1/trends/weekly/2026-W46?lang=jp").status_code == 422


def test_translations_survive_reupload(client, ingest):
    # BR-S42, BR-S43: 원본을 다시 올려도 번역 · 번역 검색이 남는다
    seed(client, ingest)
    seed_translations(client)
    ingest(make_digest("2026-11-13", [make_paper("2611.00001", title="Agent Memory", one_liner="다시 분석")]))
    assert client.get("/api/v1/papers/2611.00001?lang=ko").json()["paper"]["title"] == "에이전트 기억"
    assert client.get("/api/v1/papers?q=기억을").json()["total"] == 1
    upload(client, [make_news("ggml-org/llama-cpp-v1", title="llama.cpp v1", content="Original body v2.")])
    assert client.get("/api/v1/news?q=번역된").json()["total"] == 1
