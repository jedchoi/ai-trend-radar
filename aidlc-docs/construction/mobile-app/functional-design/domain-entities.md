# Domain Entities — mobile-app

| 엔티티 | 출처 | 비고 |
| --- | --- | --- |
| Digest, Paper, PaperBrief, HubItem, DigestSummary, TrendReport, TopicSeries, Periods, SearchResult | 서버 API (`services.md`) | 모르는 필드 무시, 선택 필드 없음 허용 (NFR-07) |
| Topic | 9개 slug + 한국어 이름 + 색 | 모르는 slug 는 `other` 로 |
| Settings | 기기 (`shared_preferences`) | serverUrl, interests (목록), askTarget (claude · chatgpt · gemini) |
| LibraryEntry | 기기 | paper (PaperBrief), status, note, savedAt |
| CachedResponse | 기기 | 경로 → JSON 문자열 |
