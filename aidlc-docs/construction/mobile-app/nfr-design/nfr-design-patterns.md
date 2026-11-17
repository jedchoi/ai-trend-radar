# NFR Design Patterns — mobile-app

| NFR | 패턴 | 위치 |
| --- | --- | --- |
| NFR-A01 | Cache-aside (네트워크 우선, 실패 시 저장본) | `lib/data/repository.dart` |
| NFR-A02 | Tolerant reader: `JsonReader` 도우미로 타입이 틀리거나 없는 필드는 기본값 | `lib/models/json.dart` |
| NFR-A03 | 요청마다 `timeout(10s)` | `lib/data/api_client.dart` |
| NFR-A04 | 링크 열기 전 scheme 검사 | `lib/ui/widgets/links.dart` |
| NFR-A05 | 가변 길이 텍스트는 `Flexible` + `maxLines`, 목록은 스크롤 | 화면 전체 |
| NFR-A06 | 의존성 주입 (`AppServices` InheritedWidget, `http.Client` 주입) | `lib/services.dart` |
