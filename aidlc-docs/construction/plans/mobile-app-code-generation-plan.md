# Code Generation 계획 — mobile-app

- 대상 story: US-01 ~ US-15
- 제약: 이 세션에는 Flutter SDK 가 없다 (pub.dev · Flutter 저장소 접근 불가). 코드 · 테스트는 작성하고, 실행은 CI (Flutter 3.41.7) 또는 사용자 Mac 에서 한다

## Steps

- [x] Step 1: 골격 — `app/pubspec.yaml`, `analysis_options.yaml`, `assets/demo/` (예시 응답 복사), `tool/bootstrap.sh` (`flutter create` 로 android · ios 폴더 생성 + 인터넷 권한)
- [x] Step 2: 모델 · JSON (BR-A02 ~ BR-A04, NFR-A02)
- [x] Step 3: 데이터 — api_client, demo_api, cache_store, repository (BR-A01, BR-A12, BR-A13), settings_store (BR-A06, BR-A13), library_store (BR-A11)
- [x] Step 4: 로직 — interest_ranker (BR-A05), ask_prompt (BR-A08)
- [x] Step 5: 화면 — Today (AC-01 ~ AC-04), Paper (AC-05 ~ AC-08, AC-13-1), Trend (AC-09 ~ AC-11), Search (AC-12), Library (AC-13), Settings (AC-04-1, AC-15)
- [x] Step 6: 단위 테스트 — `test/models_test.dart`, `test/interest_ranker_test.dart`, `test/ask_prompt_test.dart`, `test/stores_test.dart`, `test/repository_test.dart`
- [x] Step 7: 위젯 테스트 — `test/widgets/*_test.dart` (화면 6개, 텍스트 배율 1.3)
- [x] Step 8: 코드 요약 문서
