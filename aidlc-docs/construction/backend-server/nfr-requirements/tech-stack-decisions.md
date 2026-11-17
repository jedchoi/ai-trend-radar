# Tech Stack Decisions — backend-server

| 영역 | 선택 (고정 버전) | 근거 |
| --- | --- | --- |
| 언어 | Python 3.12 | 사용자가 iworship 에서 쓰는 Python · FastAPI 경험, 지원 기간 |
| 웹 프레임워크 | FastAPI 0.163.1, Starlette 1.10.0 | 형식 검사 (Pydantic) 와 API 계약 문서화, 사용자 경험 |
| 서버 | Uvicorn 0.54.0 | FastAPI 표준 ASGI 서버 |
| 형식 검사 | Pydantic 2.14.3 | 계약의 정본, 파이프라인과 같은 라이브러리 |
| DB | PostgreSQL 16 + psycopg 3.3 (연결 풀 psycopg-pool 3.3), 검색 = 소문자 검색 문자열 부분 일치 + pg_trgm GIN 색인 | 2주기 (FR-23): 사용자가 Docker Desktop 의 Postgres 사용을 요청. 원문 (최대 200,000자) · JSONB 원본 저장. 1주기의 SQLite FTS5 를 대체. 1만 건 p95 117 ms (검색) 측정 |
| HTTPS 프록시 | Caddy 2.8.4 | 인증서 자동 발급 · 갱신, 설정 파일 짧음 |
| 컨테이너 | Docker Compose | 사용자가 iworship 에서 사용 중 |
| 테스트 | pytest 9.2.0, pytest-cov 7.1.0, hypothesis 6.170.15, httpx 0.28.1 | PBT (부분) · 커버리지 |
| 정적 검사 | ruff 0.17.5 | 포맷 · lint 하나로 |
| 공급망 | pip-audit 2.10.1, CycloneDX (CI) | SECURITY-10 |

버전은 2026-11-17 PyPI 에서 설치해 확인한 값이다.
