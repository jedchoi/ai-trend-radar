# 추적성 점검 — 2주기 (Construction → Operations 경계)

점검일: 2026-11-17. 범위: FR-23 ~ FR-31, NFR-10 ~ NFR-12, US-21 ~ US-27.
방향: 요구 → 스토리 → 설계 (cycle2-design.md) → 소스 → 테스트 → 실행 결과, 그리고 역방향 (근거 없는 구현 찾기).

## 정방향

| 요구 | 스토리 · AC | 설계 | 소스 | 테스트 | 결과 |
| --- | --- | --- | --- | --- | --- |
| FR-23 Postgres · DB 자동 생성 · 기존 Postgres | US-25 (AC-25-1, 25-2) | BR-S35, 인프라 표 | `server/app/repository.py` (ensure_database, init), `config.py` (DATABASE_URL), `tool/radar-up.sh --database-url` | `test_repository_pg.py` (5), 기존 72개를 Postgres 로 | ✅ 88 passed |
| FR-24 Docker 한 명령 · 볼륨 | US-25 (AC-25-1) | 인프라 표 | `deploy/local/compose.yml`, `server/Dockerfile`, `deploy/server/docker-compose.yml` | 리허설 (가짜 docker), CI server-image 스모크 | ⚠️ 실제 Docker 는 사용자 Mac · CI |
| FR-25 HF 블로그 뉴스 · 한 번만 분석 | US-22 (AC-22-1 ~ 3) | BR-P30, P32, P33, S30, S33 | `pipeline/radar/news.py`, `runner.run_news`, `publish.upload_news`, `prompts/news.md`, 서버 news 테이블 · `/api/v1/news` | pipeline `test_news.py` (14), server `test_news.py` (8), 통합 1 | ✅ |
| FR-26 원문 (뉴스 본문 · 초록 · 주목 논문 본문 · 원본 JSON) | US-23 (AC-23-1, 23-2) | BR-P31, S31, S32 | `runner.full_text` · `attach_full_text`, `hf_client._raw_copy`, `news.extract_article`, 서버 `full_text` · `source_raw` 열 | pipeline `test_fulltext.py` (5), server `test_original_text.py` (3), 통합 1 | ✅ |
| FR-27 API (뉴스 목록 · 상세, 논문 원문 · arXiv) | US-22, US-23 | 계약 표 | `schemas.py` (NewsIn · News · NewsList · Paper.arxiv_url · has_full_text), `routes_*.py` | server 테스트, `contract/samples/news_*.json`, app `cycle2_test.dart` 파싱 | ✅ (app ⚠️ 미실행) |
| FR-28 매일 06:00 · 리포트 | US-24 (AC-24-1, 24-2) | BR-P34, P35 | `deploy/local/schedule.plist` (Hour 6), `tool/radar-daily.sh` (잠금 · 서버 깨우기), `cli daily` → run_news → run_reports | 리허설 (`radar-daily.sh` 멱등), 기존 리포트 테스트 | ⚠️ launchd 는 사용자 Mac |
| FR-29 설치 즉시 동작 | US-21 (AC-21-1, 21-2) | BR-A20 | `settings_store.dart` (기본 주소 우선순위), `services.dart` (RADAR_SERVER_URL), `tool/radar-up.sh` 5단계 · `tool/local-app.sh` | app `cycle2_test.dart` (기본 서버 주소), 기존 BR-A13 위젯 테스트 | ⚠️ 앱 미실행 |
| FR-30 앱 사용성 | US-22, US-26 (AC-26-1 ~ 4) | BR-A21 ~ A28 | `app.dart` (5탭 · 글자 크기), `news_screen.dart`, `news_detail_screen.dart`, `original_text.dart`, `read_store.dart`, `library_store.dart` (뉴스), `today_screen.dart` (소식 카드) | app 위젯 6 · 단위 8 | ⚠️ 앱 미실행 |
| FR-31 한 명령 | US-21 | 인프라 표 | `tool/radar-up.sh` | 리허설 (서버 → 백필 → 재실행), shellcheck | ✅ (Mac 실행 ⚠️) |
| NFR-10 원문 예절 3초 · 실패 계속 | US-23 | BR-P31 | `runner.ORIGINAL_PAUSE_S` | `test_run_news_uploads_recent_new_posts_once` (sleeps), `test_full_text_failure_only_empties_text` | ✅ |
| NFR-11 원문 200,000자 · 업로드 10 MB · 10건씩 | US-22, US-23 | BR-S34, P33 | `schemas.FULL_TEXT_MAX`, `config.max_body_bytes`, `publish.NEWS_BATCH` | `test_invalid_news_is_422`, `test_large_upload_up_to_ten_megabytes`, `test_full_text_limit`, `test_run_news_in_batches_of_ten` | ✅ |
| NFR-12 인계 | US-27 (AC-27-1) | - | `aidlc-docs/handoff.md`, `AGENTS.md` | 문서 검토 | ✅ |

## 역방향 (근거 없는 구현)

| 구현 | 근거 |
| --- | --- |
| `tool/test-db.sh`, CI Postgres 서비스 | FR-23 의 테스트 수단 (NFR-06 테스트) |
| 앱 오프라인 저장본 크기 제한 (`CacheStore.maxChars`) | BR-A28 (FR-21 과 FR-26 의 충돌 해소) |
| 세션 시간대 UTC 고정 (`TimeZone=UTC`) | NFR-07 호환성 (DB 서버 설정과 무관한 같은 응답) — 리허설 중 발견 |
| `radar news` 명령 | FR-25 수동 실행 · 점검용 |

ORPHAN 0, GAP 0. 실행 대기 (Deferred): 앱 테스트 54개, Docker Desktop 실제 기동, launchd 06:00, 실제 Hugging Face 수집 — 모두 사용자 Mac 필요 (handoff.md 1장).
