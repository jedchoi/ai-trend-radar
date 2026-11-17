# Tech Stack Decisions — pc-pipeline

| 영역 | 선택 | 근거 |
| --- | --- | --- |
| 언어 | Python 3.11 이상 (`tomllib`, `zoneinfo`) | macOS 기본 Python 3.9 대신 `uv` 가 Python 을 받아 실행 |
| 실행 · 의존성 | uv 0.13.9 (`uv run radar ...`), `uv.lock` | 설치 한 줄, 잠금 파일 |
| HTTP | httpx 0.28.1 | 시간 제한 · MockTransport 테스트 |
| 형식 검사 | Pydantic 2.14.3 | 서버와 같은 라이브러리 |
| AI SDK | 쓰지 않음 (HTTP 직접 · CLI 호출) | 의존성 최소, 제공자 교체 용이 |
| 테스트 | pytest 9.2.0, pytest-cov 7.1.0, hypothesis 6.170.15 | 서버와 같음 |
