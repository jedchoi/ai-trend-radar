# Code Summary — backend-server

## 파일

| 파일 | 내용 | 규칙 |
| --- | --- | --- |
| `server/app/schemas.py` | API 계약 (요청 · 응답 형식, 입력 검증) | BR-S04, NFR-S06, NFR-S12 |
| `server/app/periods.py` | 기간 · 급상승 · 연속 일수 순수 함수 | BR-S08, BR-S12, BR-S14 |
| `server/app/repository.py` | SQLite (FTS5) 저장 · 조회, 날짜 단위 트랜잭션, ingest_log | BR-S02, BR-S03, BR-S05 ~ BR-S11, NFR-S11 |
| `server/app/trends.py` | 주 · 월 통계, 시계열, 기간 목록 | BR-S13 ~ BR-S20 |
| `server/app/security.py` | 업로드 토큰 (해시 비교, 닫힌 실패) | BR-S01 |
| `server/app/middleware.py` | 속도 제한, 본문 크기, 보안 헤더, 접근 로그, 최후 오류 처리 | NFR-S05 ~ NFR-S09 |
| `server/app/routes_public.py`, `routes_ingest.py`, `main.py` | 라우터 · 조립 · 오류 처리기 | BR-S21, BR-S22 |
| `server/tools/make_samples.py` | 예시 응답 → `contract/samples/*.json` | mobile-app 입력 |
| `server/Dockerfile`, `requirements.lock` | 해시 고정 설치, 비 root, healthcheck | SECURITY-06, 10 |

## TDD 기록

| 단계 | 결과 |
| --- | --- |
| RED | 테스트 71개 작성 후 stub 상태에서 67 실패 · 4 통과 (토큰 해시 길이 · 문서 화면 켜짐 등 stub 과 우연히 맞은 보호 테스트) |
| GREEN | 71 통과 |
| REFACTOR | ruff 형식 · 규칙 정리 (줄 길이 120), 동작 변화 없음, 71 통과 유지 |

## 실행 결과 (2026-11-17)

| 명령 | 결과 |
| --- | --- |
| `pytest --cov=app` | 71 passed, 커버리지 96% (라인 757 중 17 미실행) |
| `pytest -m perf` | 1 passed. p95 (ms): digests/latest 14.7, 검색 46.8, 필터 12.2, weekly 23.7, monthly 50.2, series 14.2, paper 45.3 (기준 300) |
| `ruff check`, `ruff format --check` | 통과 |
| `pip-audit -r requirements.txt` | 알려진 취약점 없음 |
| `uvicorn` 실기동 + curl | health 200 · 보안 헤더 확인, 토큰 없는 업로드 401, 토큰 업로드 200 |
| Docker 이미지 빌드 | 미실행 (이 환경에서 Docker Hub 접근 불가). CI 에서 빌드 |

## 설계와 다른 점 (CG-7)

- TDD 스냅샷 스크립트 (`tdd_snapshot.py`) 는 `backend/` 구조를 전제로 해 쓰지 않았다. RED · GREEN 결과는 위 표로 기록
- 계획에 없던 추가: `server/requirements.lock` (해시 고정, SECURITY-10 강화), `HubItem.url` 응답 필드 (AC-03-3 을 앱에서 쉽게 처리)
