# Application Design 요약

- **구조**: PC 파이프라인 (Python) → backend 서버 (FastAPI + PostgreSQL, 2주기에 SQLite 에서 변경) → 모바일 앱 (Flutter). 서버 API 가 유일한 계약 (`services.md`)
- **결정 1 (트렌드 계산 위치)**: 서버가 저장 데이터로 통계를 계산, 파이프라인은 해석 문장만 올림 (계획 Q1)
- **결정 2 (AI 호출)**: SDK 없이 HTTP 직접 호출 + 구독형 CLI 호출 (`cli` 제공자). AI 없는 `none` 제공자로 전체 흐름이 돈다 (계획 Q2, NFR-01)
- **결정 3 (앱 상태)**: ChangeNotifier + ListenableBuilder, 외부 패키지는 `http`, `shared_preferences`, `url_launcher` 만 (계획 Q3)
- **보관함 · 관심 키워드**: 기기 안 저장 (사용자 계정 없음, Q7)
- 상세: `components.md`, `component-methods.md`, `services.md`, `component-dependency.md`
