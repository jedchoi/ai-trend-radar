# 추적성 점검 — 4주기 (같은 응답에 두 언어)

점검일: 2026-11-18. 범위: FR-38 ~ FR-42, US-32 ~ US-34.

| 요구 | 스토리 · AC | 설계 | 소스 | 테스트 | 결과 |
| --- | --- | --- | --- | --- | --- |
| FR-38 요약류 두 언어 저장 | US-32, US-34 | 계약 (번역 업로드 허용 필드) | `schemas.PaperTranslation` · `NewsTranslation`, `translate._digest_jobs` · `_news_job` | server `test_upload_requires_token_and_summary_fields_only`, pipeline `test_translates_summaries_into_the_other_language` | ✅ |
| FR-39 같은 응답에 i18n {ko, en} | US-32 (AC-32-2) | BR-S50, BR-S51 | `server/app/i18n.py` (build_i18n), `repository.translations_all`, 응답 모델 `i18n` | `test_digest_has_both_languages_in_one_response`, `test_paper_detail_related_search_news_and_report`, 통합 | ✅ |
| FR-40 앱이 골라 보여 줌 · 다시 받지 않음 · 준비 중 | US-32 (AC-32-1, 32-3) | BR-A50, A51, A53 | `app/lib/models/i18n.dart`, 모델 getter, `repository` (lang 없음), `settings.sourceKey` (언어 제외) | app `cycle4_test.dart` (모델 · 요청 · 버튼 전환 요청 수 · 준비 중 · 보관함) | ⚠️ 앱 미실행 |
| FR-41 원문 영어 그대로 | US-33 (AC-33-1) | 계약, BR-A52 | i18n 에 원문 필드 없음, 번역 업로드 거부, 앱 원문 영역 "원문" | server · pipeline · 통합 · app 테스트 | ✅ (앱 ⚠️) |
| FR-42 반대 언어 채우기 (한글 규칙) | US-34 (AC-34-1, 34-2) | BR-P50, BR-P51 | `translate.base_lang` · `other_lang`, 매일 · 백필 · `radar translate` | `test_base_lang_rule`, `test_second_run_skips_done_and_retranslates_changed`, `test_base_value_wins_over_same_language_translation` | ✅ |

역방향: 없음 (lang 매개변수 · untranslated 응답 필드 · 긴 본문 번역은 삭제). GAP 0 · ORPHAN 0. 실행 대기: 앱 테스트, 실제 번역 실행.
