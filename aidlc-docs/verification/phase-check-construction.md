# Traceability Check 결과 — ② Construction (Construction → Operations)

- **점검 시각**: 2026-11-17T14:10:00Z
- **회차**: 1
- **대상 결정**: 인자 `construction` (사용자 위임에 따라 AI 가 Build and Test 후 실행)

## 1. 요약

| 항목 | 값 |
| --- | --- |
| 판정 | 조건부 통과 (mobile-app 테스트 실행 대기) |
| 정방향 대상 | Story 20 |
| OK (테스트 실행 · 통과) | 8 (US-16 ~ US-20 전부, US-01 · US-07 · US-12 의 서버 부분) |
| Deferred (테스트 작성됨 · 실행 대기) | 15 스토리의 앱 부분 (US-01 ~ US-15) |
| GAP | 0 |
| ORPHAN | 0 |

## 2. 정방향 추적 (요약)

| Story | Unit | 소스 · 테스트 | 실행 결과 | 상태 |
| --- | --- | --- | --- | --- |
| US-01 ~ US-03 | backend-server · mobile-app | `server/tests/test_digests.py`, `app/test/widget_test.dart` | 서버 PASS / 앱 미실행 | OK / Deferred |
| US-04 | mobile-app | `app/test/logic_test.dart`, `stores_test.dart`, `widget_test.dart` | 미실행 | Deferred |
| US-05 ~ US-07 | 세 unit | `server/tests/test_papers.py`, `pipeline/tests/test_analyze.py`, `app/test/widget_test.dart` | 서버 · 파이프라인 PASS / 앱 미실행 | OK / Deferred |
| US-08 | mobile-app | `app/test/logic_test.dart` | 미실행 | Deferred |
| US-09 ~ US-11 | backend-server · mobile-app | `server/tests/test_trends.py`, `test_periods_pbt.py`, 앱 위젯 | 서버 PASS / 앱 미실행 | OK / Deferred |
| US-12 | backend-server · mobile-app | `server/tests/test_papers.py`, `app/test/repository_test.dart` | 서버 PASS / 앱 미실행 | OK / Deferred |
| US-13 ~ US-15 | mobile-app | `app/test/stores_test.dart`, `widget_test.dart` | 미실행 | Deferred |
| US-16 ~ US-18 | pc-pipeline | `pipeline/tests/test_runner.py`, `test_hf_client.py`, `test_selection.py` | PASS | OK |
| US-19 | 서버 · 파이프라인 | `server/tests/test_ingest.py`, `integration/` | PASS | OK |
| US-20 | 서버 · 파이프라인 | `pipeline/tests/test_runner.py::test_reports_*`, `server/tests/test_ingest.py::test_report_*` | PASS | OK |

## 3. 역방향 추적

| 항목 | 상태 | 사유 |
| --- | --- | --- |
| 데모 모드 (`demo_api.dart`) | OK | mobile-app Functional Design 계획 Q1 · BR-A13 |
| `radar token` · `check` 명령 | OK | US-19 운영 (토큰 생성), BR-P11 |

## 4. 보완 제안

| 대상 | 문제 | 담당 |
| --- | --- | --- |
| mobile-app 테스트 | Flutter 미실행 | 사용자 · CI: `cd app && tool/bootstrap.sh && flutter test` |

## 7. 사람 확인

- [ ] 점검 결과 검토 완료 (승인자: [ ], 시각: [ ])
