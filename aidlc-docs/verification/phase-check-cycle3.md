# 추적성 점검 — 3주기 (한국어 · 영어)

점검일: 2026-11-18. 범위: FR-32 ~ FR-37, NFR-13 ~ NFR-15, US-28 ~ US-31.

| 요구 | 스토리 · AC | 설계 | 소스 | 테스트 | 결과 |
| --- | --- | --- | --- | --- | --- |
| FR-32 앱 언어 전환 · 유지 | US-28 (AC-28-1, 28-2) | BR-A30, A32, A33 | `app/lib/l10n/strings.dart`, `settings_store.dart` (language), `app.dart` (LanguageRebuilder), `ui/widgets/language_button.dart`, 모든 화면 `tr()` | app `cycle3_test.dart` (설정 유지, 버튼 전환, 상세 화면 전환) | ⚠️ 앱 미실행 |
| FR-33 서버 lang · untranslated · 호환 | US-28 (AC-28-3) | BR-S40 | `server/app/i18n.py`, `routes_public.py` (LangQuery), `schemas.py` (untranslated) | server `test_i18n.py` (digest · paper · news · report · 호환), app 파싱 · 번역 준비 중 표시 | ✅ (앱 ⚠️) |
| FR-34 번역 범위 (원문 본문까지) | US-29 (AC-29-1, 29-2) | 계약 표, BR-P40 | `pipeline/radar/translate.py` (_digest_jobs · _news_jobs · 리포트 · 긴 본문), `prompts/translate*.md` | pipeline `test_translates_short_first_then_long_and_uploads`, 통합 | ✅ |
| FR-35 PC 가 번역 · 한 번만 · 바뀌면 다시 · 짧은 것 먼저 | US-30 (AC-30-1, 30-3) | BR-P40 ~ P43, P45 | `translate.py` (해시 상태), `runner.run_translate`, `cli` (daily 끝 · translate 명령) | `test_second_run_skips_done_and_retranslates_changed`, `test_cli_translate_and_daily_order` | ✅ |
| FR-36 지난 데이터 한 번에 · 이어서 | US-30 (AC-30-2) | BR-P44 | `tool/radar-daily.sh --translate 90`, 백필 끝 번역 | `test_time_limit_stops_and_keeps_progress` | ✅ (실제 실행 ⚠️) |
| FR-37 한국어로 검색 | US-31 (AC-31-1) | BR-S42 | `repository._refresh_search_i18n`, search_i18n 열 · 색인 | `test_paper_detail_and_related_and_search`, `test_news_list_and_detail`, `test_translations_survive_reupload`, 통합 | ✅ |
| NFR-13 시간 상한 | US-30 | BR-P44 | `TranslateConfig.max_minutes`, `StopTranslating` | 시간 상한 테스트 | ✅ |
| NFR-14 형식 검사 · 재요청 · 건너뛰기 | US-30 | BR-P42 | `same_shape`, `MIN_RATIO`, 재요청 | `test_bad_output_is_retried_then_skipped`, `test_batch_asks_again_for_missing_ids`, `test_too_short_translation_fails_whole_text` | ✅ |
| NFR-15 성능 | - | - | 목록은 긴 필드 빼고 번역 조회 (`fields - 'full_text' - 'content'`) | perf 테스트 p95 127 ms | ✅ |

역방향: `tool/radar-daily.sh` 의 매일 서버 갱신 (`radar-up.sh --server-only`) — 새 서버 코드 (번역 API) 를 06:00 에 자동 반영하기 위한 운영 수단 (FR-33 의 배포). 백필 뉴스 순서 수정은 2주기 버그 수정 (audit 00:30). ORPHAN 0, GAP 0. 실행 대기: 앱 테스트, 실제 번역 실행 · 품질 확인.

## 개정 (2026-11-18 01:10)

| 변경 | 반영 위치 | 테스트 |
| --- | --- | --- |
| FR-34: 논문 원문 (초록 · 본문) 영어 유지 | requirements · stories (AC-29-1) · cycle3-design (계약 표, BR-P40 · P41 · A35) · `schemas.PaperTranslation` · `i18n.PAPER_FIELDS` · `translate._digest_jobs` · `paper_screen._original` | `test_translation_upload_requires_token_and_valid_shape` (422), `test_digest_in_english_and_korean`, `test_translates_short_first_then_long_and_uploads`, 통합, app `cycle3_test` · `widget_test` |
| BR-P34: 뉴스 먼저 | cycle2-design · `runner.run_daily` · `runner.run_backfill` | `test_daily_uploads_news_before_papers`, `test_backfill_uploads_news_before_slow_ai_phase` |

GAP 0 · ORPHAN 0 유지.
