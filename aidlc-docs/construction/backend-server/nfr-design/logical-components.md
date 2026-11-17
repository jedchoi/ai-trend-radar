# Logical Components — backend-server

| 구성 요소 | 파일 | 역할 |
| --- | --- | --- |
| Settings | `server/app/config.py` | 환경 변수 (`DATABASE_URL`, `DB_POOL_SIZE`, `INGEST_TOKEN_SHA256`, `ENABLE_DOCS`, 속도 한도, `MAX_BODY_BYTES`) |
| Logging | `server/app/logging_setup.py` | JSON 로그 포매터 |
| Middleware | `server/app/middleware.py` | 본문 크기 제한 · 속도 제한 · 보안 헤더 · 접근 로그 · 요청 id |
| Security | `server/app/security.py` | 업로드 토큰 의존성 |
| Schemas | `server/app/schemas.py` | 계약 |
| Periods | `server/app/periods.py` | 기간 · 급상승 · 연속 일수 순수 함수 |
| Repository | `server/app/repository.py` | PostgreSQL 접근 (연결 풀, 시작 시 DB · 스키마 생성) |
| Trends | `server/app/trends.py` | 통계 조합 |
| Routers | `server/app/routes_public.py`, `server/app/routes_ingest.py` | HTTP |
| App | `server/app/main.py` | 조립, 오류 처리기 |
