# Tech Stack Decisions — backend-server

| 영역 | 선택 (고정 버전) | 근거 |
| --- | --- | --- |
| 언어 | Python 3.12 | 사용자가 iworship 에서 쓰는 Python · FastAPI 경험, 지원 기간 |
| 웹 프레임워크 | FastAPI 0.163.1, Starlette 1.10.0 | 형식 검사 (Pydantic) 와 API 계약 문서화, 사용자 경험 |
| 서버 | Uvicorn 0.54.0 | FastAPI 표준 ASGI 서버 |
| 형식 검사 | Pydantic 2.14.3 | 계약의 정본, 파이프라인과 같은 라이브러리 |
| DB | SQLite (표준 라이브러리, FTS5) | 하루 1회 쓰기 · 읽기 위주 · 단일 서버. 별도 DB 서버 운영 부담 없음. 1만 건 기준 NFR-S01 충족 예상 (Build and Test 에서 측정) |
| HTTPS 프록시 | Caddy 2.8.4 | 인증서 자동 발급 · 갱신, 설정 파일 짧음 |
| 컨테이너 | Docker Compose | 사용자가 iworship 에서 사용 중 |
| 테스트 | pytest 9.2.0, pytest-cov 7.1.0, hypothesis 6.170.15, httpx 0.28.1 | PBT (부분) · 커버리지 |
| 정적 검사 | ruff 0.17.5 | 포맷 · lint 하나로 |
| 공급망 | pip-audit 2.10.1, CycloneDX (CI) | SECURITY-10 |

버전은 2026-11-17 PyPI 에서 설치해 확인한 값이다.
