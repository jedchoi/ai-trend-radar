# Tech Stack Decisions — mobile-app

| 영역 | 선택 | 근거 |
| --- | --- | --- |
| 프레임워크 | Flutter 3.41.7 (CI 고정, TidalConnect 와 같음), Material 3 | 사용자 기존 스택 |
| HTTP | `http` ^1.2.2 | 표준적, `MockClient` 로 테스트 |
| 저장 | `shared_preferences` ^2.3.2 | 설정 · 보관함 · 캐시 (작은 JSON) |
| 링크 | `url_launcher` ^6.3.1 | 외부 브라우저 |
| 상태 | ChangeNotifier + ListenableBuilder | 패키지 없음 |
| 차트 | CustomPainter | 패키지 없음 |
| 정적 검사 | `flutter_lints` ^5.0.0 | Flutter 기본 규칙 |

버전 범위는 2024~2025 년에 공개된 안정 버전 기준의 하한이다. 이 세션에는 Flutter · pub 접근이 없어 실제 해석 버전은 첫 `flutter pub get` 의 `pubspec.lock` 으로 고정한다.
