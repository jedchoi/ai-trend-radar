import hashlib

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import AUTH, TOKEN, make_digest, make_hub, make_paper

URL = "/api/v1/ingest/daily"


def test_missing_token_is_rejected_and_nothing_saved(client):
    # BR-S01 / AC-19-1: 토큰 없음 → 401, 저장 0건
    resp = client.post(URL, json=make_digest("2026-11-13", [make_paper("2611.00001")]))
    assert resp.status_code == 401
    assert client.get("/api/v1/digests/2026-11-13").status_code == 404


def test_wrong_token_is_rejected(client):
    # BR-S01 / AC-19-1: 틀린 토큰 → 401
    resp = client.post(URL, json=make_digest("2026-11-13"), headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401
    assert resp.json() == {"error": "unauthorized"}


def test_non_bearer_scheme_is_rejected(client):
    # BR-S01: Bearer 형식이 아니면 401
    resp = client.post(URL, json=make_digest("2026-11-13"), headers={"Authorization": f"Basic {TOKEN}"})
    assert resp.status_code == 401


def test_unconfigured_token_fails_closed(clean_db):
    # BR-S01: 서버에 토큰 해시가 없으면 503 (닫힌 실패)
    settings = Settings(database_url=clean_db, ingest_token_sha256="")
    with TestClient(create_app(settings)) as c:
        resp = c.post(URL, json=make_digest("2026-11-13"), headers=AUTH)
    assert resp.status_code == 503


def test_valid_upload_returns_count(client):
    # FR-10: 저장한 논문 수 반환
    payload = make_digest("2026-11-13", [make_paper("2611.00001"), make_paper("2611.00002")])
    resp = client.post(URL, json=payload, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == {"date": "2026-11-13", "papers": 2}


def test_reupload_replaces_the_whole_day(client, ingest):
    # BR-S02 / AC-19-2: 같은 날짜 재업로드 → 통째로 교체
    ingest(
        make_digest(
            "2026-11-13", [make_paper("2611.00001"), make_paper("2611.00002")], hub=[make_hub("model", 1, "org/a")]
        )
    )
    ingest(
        make_digest("2026-11-13", [make_paper("2611.00003")], hub=[make_hub("model", 1, "org/b")], headline=["새 줄"])
    )
    digest = client.get("/api/v1/digests/2026-11-13").json()
    assert [p["id"] for p in digest["papers"]] == ["2611.00003"]
    assert [h["id"] for h in digest["hub"]] == ["org/b"]
    assert digest["headline"] == ["새 줄"]


def test_paper_moves_to_new_date_when_reuploaded_elsewhere(client, ingest):
    # BR-S03: 다른 날짜에 이미 있는 논문 → 새 날짜로 이동
    ingest(make_digest("2026-11-12", [make_paper("2611.00001")]))
    ingest(make_digest("2026-11-13", [make_paper("2611.00001")]))
    assert client.get("/api/v1/digests/2026-11-12").json()["papers"] == []
    assert client.get("/api/v1/papers/2611.00001").json()["paper"]["date"] == "2026-11-13"


def test_invalid_topic_is_422_and_nothing_saved(client):
    # BR-S04 / AC-19-3: 모르는 topic → 422, 저장 0건
    payload = make_digest("2026-11-13", [make_paper("2611.00001", topic="crypto")])
    resp = client.post(URL, json=payload, headers=AUTH)
    assert resp.status_code == 422
    assert client.get("/api/v1/digests/2026-11-13").status_code == 404


def test_validation_error_does_not_echo_input(client):
    # BR-S04: 오류 응답에 입력 값을 넣지 않음
    secret = "SECRET-INPUT-VALUE"
    payload = make_digest("2026-11-13", [make_paper("2611.00001", topic=secret)])
    resp = client.post(URL, json=payload, headers=AUTH)
    assert resp.status_code == 422
    assert secret not in resp.text
    assert resp.json()["error"] == "invalid_request"


def test_too_many_headline_lines_is_422(client):
    # BR-S04: 세 줄 초과 → 422
    resp = client.post(URL, json=make_digest("2026-11-13", headline=["a", "b", "c", "d"]), headers=AUTH)
    assert resp.status_code == 422


def test_duplicate_paper_ids_are_422(client):
    # BR-S04: 같은 업로드 안 중복 id → 422
    payload = make_digest("2026-11-13", [make_paper("2611.00001"), make_paper("2611.00001")])
    assert client.post(URL, json=payload, headers=AUTH).status_code == 422


def test_unknown_field_is_422(client):
    # BR-S04: 계약에 없는 필드 → 422 (오타 방지)
    payload = make_digest("2026-11-13")
    payload["extra"] = 1
    assert client.post(URL, json=payload, headers=AUTH).status_code == 422


def test_date_far_in_future_is_422(client):
    # 값 범위: 오늘 + 1일 초과 → 422
    assert client.post(URL, json=make_digest("2099-01-01"), headers=AUTH).status_code == 422


def test_failure_mid_transaction_rolls_back(client, ingest, monkeypatch):
    # BR-S02 / NFR-S02: 중간 오류 → 기존 데이터 유지
    ingest(make_digest("2026-11-13", [make_paper("2611.00001")]))
    from app import repository

    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(repository, "_insert_hub", boom)
    payload = make_digest("2026-11-13", [make_paper("2611.00009")], hub=[make_hub("model", 1, "org/x")])
    resp = client.post(URL, json=payload, headers=AUTH)
    assert resp.status_code == 500
    assert resp.json() == {"error": "internal_error"}
    assert [p["id"] for p in client.get("/api/v1/digests/2026-11-13").json()["papers"]] == ["2611.00001"]


def test_report_upload_and_overwrite(client, ingest):
    # BR-S21 / AC-20-1: 리포트 업로드 · 덮어쓰기
    ingest(make_digest("2026-11-10", [make_paper("2611.00001")]))
    url = "/api/v1/ingest/report"
    body = {"period": "week", "key": "2026-W46", "narrative": "첫 문장", "provider": "none"}
    assert client.post(url, json=body, headers=AUTH).json() == {"period": "week", "key": "2026-W46"}
    body["narrative"] = "바뀐 문장"
    client.post(url, json=body, headers=AUTH)
    report = client.get("/api/v1/trends/weekly/2026-W46").json()
    assert report["narrative"] == "바뀐 문장"
    assert report["narrative_provider"] == "none"


def test_report_key_must_match_period(client):
    # BR-S21: 주 리포트에 월 키 → 422
    body = {"period": "week", "key": "2026-11", "narrative": "x"}
    assert client.post("/api/v1/ingest/report", json=body, headers=AUTH).status_code == 422


def test_report_requires_token(client):
    # BR-S01: 리포트도 토큰 필요
    body = {"period": "month", "key": "2026-11", "narrative": "x"}
    assert client.post("/api/v1/ingest/report", json=body).status_code == 401


def test_ingest_is_logged_for_audit(client, ingest, settings):
    # NFR-S11: 업로드마다 ingest_log 1행
    import psycopg

    ingest(make_digest("2026-11-13", [make_paper("2611.00001")]))
    with psycopg.connect(settings.database_url) as conn:
        rows = conn.execute("select kind, key, count from ingest_log").fetchall()
    assert rows == [("daily", "2026-11-13", 1)]


def test_token_hash_is_what_server_stores():
    # NFR-S03: 서버 설정은 토큰 해시만
    assert len(hashlib.sha256(TOKEN.encode()).hexdigest()) == 64
