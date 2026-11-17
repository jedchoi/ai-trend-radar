# Code Summary — mobile-app

| 파일 | 내용 | 규칙 |
| --- | --- | --- |
| `app/lib/models/{json,topic,models}.dart` | 너그러운 JSON 읽기, 주제 9개 (색 · 한국어 이름), API 모델 | NFR-A02 |
| `app/lib/data/api_client.dart`, `demo_api.dart` | HTTP (10초 제한) · 데모 (앱 포함 예시 응답) | BR-A13, NFR-A03 |
| `app/lib/data/repository.dart`, `cache_store.dart` | 네트워크 우선 · 실패 시 저장본 | BR-A12 |
| `app/lib/data/settings_store.dart`, `library_store.dart` | 서버 주소 · 관심 키워드 · 묻기 대상, 보관함 | BR-A06, BR-A11, BR-A13 |
| `app/lib/logic/interest_ranker.dart`, `ask_prompt.dart` | 관심 매칭 · 정렬, 묻기 글 | BR-A05, BR-A08 |
| `app/lib/ui/screens/*.dart` | 오늘 · 논문 요약 · 트렌드 · 검색 · 보관함 · 설정 | US-01 ~ US-15 |
| `app/lib/ui/widgets/*.dart` | 카드 · 행 · Hub · 막대 · 선 차트 (CustomPainter) | BR-A04, BR-A09 |
| `app/test/*.dart` | 단위 (모델 · 로직 · 저장소 · 저장소 계층) 35개 내외, 위젯 13개 | NFR-A06 |
| `app/tool/bootstrap.sh` | `flutter create` 로 android · ios 생성 + 인터넷 권한 | - |

## 실행 결과

| 항목 | 결과 |
| --- | --- |
| `flutter test` | 40 passed (사용자 Mac, 2026-11-17). `flutter analyze` 는 CI 에서 |
| 코드 검토 | 사람이 읽는 수준의 정적 검토만 함 (import · 타입 · 폐기 예정 API 회피: `withValues`, `surfaceContainerHighest`, Radio 대신 ChoiceChip) |
| 예시 응답 동기화 | `contract/samples` == `app/assets/demo` (diff 통과) |

## 설계와 다른 점 (CG-7)

- 계획에 없던 추가: 데모 모드 (서버 주소가 없을 때, 계획 Q1 답변으로 추가), 키워드 표시 (상세 화면)
- 푸시 알림 · 따라잡기 등 "다음 · 나중" 기능은 범위 밖 (requirements.md)
