# NFR Design Patterns — backend-server

| NFR | 패턴 | 구현 위치 |
| --- | --- | --- |
| NFR-S01 성능 | FTS5 색인, `papers(date)` · `papers(upvotes)` · `paper_keywords(keyword)` · `hub_items(kind, item_id, date)` 색인, WAL 모드, 기간 통계는 SQL 집계 | `repository.py`, `trends.py` |
| NFR-S02 실패 격리 | 단위 작업 (Unit of Work): `with conn:` 트랜잭션 안에서 삭제 · 삽입, 예외 시 롤백 | `repository.upsert_digest` |
| NFR-S03 인증 | 토큰 해시 비교 (`hmac.compare_digest`), 설정 없음 = 닫힌 실패 | `security.py` |
| NFR-S04 전송 | 리버스 프록시 TLS 종단, 앱은 내부 네트워크 | `deploy/server/` |
| NFR-S05 속도 제한 | IP 별 고정 창 카운터 (메모리, 60초), 경로 그룹별 한도 | `middleware.py` |
| NFR-S06 입력 검증 | Pydantic 제약 (길이 · 정규식 · 범위), 경로 값 정규식, 본문 크기 제한 미들웨어, FTS 질의 정화 | `schemas.py`, `middleware.py`, `repository.py` |
| NFR-S07 보안 헤더 | 응답 헤더 미들웨어 | `middleware.py` |
| NFR-S08 로깅 | 구조화 로그 (JSON 한 줄), 요청 id | `middleware.py`, `logging_setup.py` |
| NFR-S09 오류 | 전역 예외 처리기 + 검증 오류 처리기 (입력 값 제거) | `main.py` |
| NFR-S11 감사 | 추가 전용 `ingest_log` | `repository.py` |
| NFR-S13 테스트 | 순수 함수 분리 (`periods.py`) + hypothesis | `tests/test_periods_pbt.py` |
