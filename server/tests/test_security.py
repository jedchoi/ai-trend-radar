import hashlib

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import AUTH, TOKEN, make_digest


def _client(tmp_path, **kw):
    settings = Settings(
        db_path=str(tmp_path / "s.db"), ingest_token_sha256=hashlib.sha256(TOKEN.encode()).hexdigest(), **kw
    )
    return TestClient(create_app(settings))


def test_security_headers_on_every_response(client):
    # NFR-S07
    for path in ("/api/v1/health", "/api/v1/digests/latest", "/nope"):
        headers = client.get(path).headers
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert headers["referrer-policy"] == "no-referrer"
        assert headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
        assert "x-request-id" in headers


def test_public_rate_limit(tmp_path):
    # NFR-S05: 공개 API 한도 초과 → 429
    with _client(tmp_path, public_rate_per_min=3) as c:
        codes = [c.get("/api/v1/health").status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_ingest_rate_limit_is_separate(tmp_path):
    # NFR-S05: 업로드 한도는 따로
    with _client(tmp_path, ingest_rate_per_min=1, public_rate_per_min=100) as c:
        first = c.post("/api/v1/ingest/daily", json=make_digest("2026-11-13"), headers=AUTH).status_code
        second = c.post("/api/v1/ingest/daily", json=make_digest("2026-11-13"), headers=AUTH).status_code
        public = c.get("/api/v1/health").status_code
    assert (first, second, public) == (200, 429, 200)


def test_body_size_limit(tmp_path):
    # NFR-S06: 본문 최대 크기 초과 → 413
    with _client(tmp_path, max_body_bytes=1000) as c:
        payload = make_digest("2026-11-13", headline=["x" * 300, "y" * 300, "z" * 300])
        payload["provider"] = "none"
        big = {**payload, "papers": []}
        resp = c.post("/api/v1/ingest/daily", json=big | {"headline": ["가" * 300] * 3}, headers=AUTH)
    assert resp.status_code == 413
    assert resp.json() == {"error": "payload_too_large"}


def test_docs_disabled_by_default(client):
    # NFR-S09: 운영에서 문서 화면 끔
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_docs_enabled_when_configured(tmp_path):
    with _client(tmp_path, enable_docs=True) as c:
        assert c.get("/openapi.json").status_code == 200


def test_unknown_route_returns_generic_error(client):
    # BR-S22 / NFR-S09
    resp = client.get("/api/v1/unknown")
    assert resp.status_code == 404
    assert resp.json() == {"error": "not_found"}


def test_write_methods_not_allowed_on_public_routes(client):
    # SECURITY-08: 공개 경로는 읽기 전용
    resp = client.delete("/api/v1/digests/2026-11-13")
    assert resp.status_code == 405
    assert resp.json() == {"error": "method_not_allowed"}


def test_auth_failure_is_logged_as_security_event(client, caplog):
    # NFR-S08: 인증 실패 → security_event, 토큰 원문 기록 안 함
    import logging

    with caplog.at_level(logging.WARNING, logger="radar.security"):
        client.post(
            "/api/v1/ingest/daily",
            json=make_digest("2026-11-13"),
            headers={"Authorization": "Bearer leaked-token-value"},
        )
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "auth_failed" in text
    assert "leaked-token-value" not in text


def test_access_log_line(client, caplog):
    # NFR-S08: 요청마다 접근 로그
    import json
    import logging

    with caplog.at_level(logging.INFO, logger="radar.access"):
        client.get("/api/v1/health")
    record = json.loads(caplog.records[-1].getMessage())
    assert record["path"] == "/api/v1/health"
    assert record["status"] == 200
    assert "duration_ms" in record


def test_rate_limit_tells_client_when_to_retry(tmp_path):
    # NFR-S05: 429 에 Retry-After (초) 를 붙여 파이프라인이 기다렸다 다시 보낼 수 있게
    with _client(tmp_path, ingest_rate_per_min=1, public_rate_per_min=100) as c:
        c.post("/api/v1/ingest/daily", json=make_digest("2026-11-13"), headers=AUTH)
        resp = c.post("/api/v1/ingest/daily", json=make_digest("2026-11-13"), headers=AUTH)
    assert resp.status_code == 429
    assert 1 <= int(resp.headers["retry-after"]) <= 60
