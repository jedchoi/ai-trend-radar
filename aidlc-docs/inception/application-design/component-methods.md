# 컴포넌트 메서드 (Component Methods)

> 상세 업무 규칙은 Functional Design 에서 정한다. 여기는 서명과 목적만.

## backend-server

| 컴포넌트 | 메서드 | 목적 |
| --- | --- | --- |
| C-S3 | `require_ingest_token(authorization) -> None` | Bearer 토큰의 SHA-256 을 설정 해시와 상수 시간 비교, 실패 시 401 · 미설정 시 503 |
| C-S4 | `upsert_digest(digest: DigestIngest, client_ip) -> int` | 날짜 단위 트랜잭션으로 기존 날짜 데이터 교체, 저장한 논문 수 반환 |
| C-S4 | `list_digests(limit) -> list[DigestSummary]` | 최신순 날짜 목록 |
| C-S4 | `get_digest(date) -> Digest \| None` | 일일 요약 + 논문 + Hub (신규 · 체류 포함) |
| C-S4 | `latest_date() -> date \| None` | 가장 최근 날짜 |
| C-S4 | `get_paper(id) -> Paper \| None`, `related_papers(id, limit) -> list[PaperBrief]` | 상세, 같은 키워드 이전 논문 |
| C-S4 | `search_papers(q, topic, since, until, featured, limit, offset) -> (list[PaperBrief], total)` | FTS5 검색 + 필터 |
| C-S4 | `upsert_report(period, key, narrative, provider, client_ip)`, `get_report(period, key)` | 리포트 문장 |
| C-S5 | `period_stats(period, key) -> TrendReport` | 주 · 월 통계 계산 |
| C-S5 | `topic_series(weeks) -> TopicSeries` | 주제별 주간 시계열 |
| C-S5 | `available_periods() -> Periods` | 데이터가 있는 주 · 월 목록 |

## pc-pipeline

| 컴포넌트 | 메서드 | 목적 |
| --- | --- | --- |
| C-P1 | `daily_papers(date) -> list[RawPaper]` | 10편 단위 페이지 수집 |
| C-P1 | `trending(kind, limit) -> list[HubItem]` | 모델 · 데이터셋 · Spaces |
| C-P1 | `paper_markdown(id, max_chars) -> str \| None` | 주목 논문 본문 |
| C-P2 | `classify(text, keywords) -> Topic` | 키워드 규칙 분류 |
| C-P3 | `score(paper, focus) -> float`, `select_featured(papers, n, focus) -> set[id]` | 선별 |
| C-P4 | `analyze_day(raw_papers, featured, provider) -> AnalyzedDay` | 분석 전체 (대체 포함) |
| C-P4 | `narrative(stats, provider) -> str` | 리포트 문장 |
| C-P5 | `Provider.complete(system, user) -> str` | 제공자 공통 인터페이스 |
| C-P7 | `upload_digest(payload)`, `upload_report(...)`, `fetch_stats(period, key)` | 서버 통신 |
| C-P8 | `run_daily(date \| None, backfill)`, `run_reports(today)` | 실행 · 기록 |
| C-P9 | `load_config(path) -> Config`, `main(argv)` | 설정 · 명령 |

## mobile-app

| 컴포넌트 | 메서드 | 목적 |
| --- | --- | --- |
| C-A1 | `latestDigest()`, `digest(date)`, `digests()`, `paper(id)`, `search(query)`, `weekly(key)`, `monthly(key)`, `series(weeks)`, `periods()` | API 호출 |
| C-A2 | `read(key)`, `write(key, json)` | 응답 캐시 |
| C-A3 | `serverUrl`, `interests`, `askTarget` + setter | 설정 |
| C-A4 | `toggle(paper)`, `setStatus(id, status)`, `setNote(id, note)`, `items(filter)` | 보관함 |
| C-A6 | `matches(paper, interests) -> List<String>`, `rank(papers, interests) -> List<Paper>` | 관심 정렬 |
| C-A7 | `build(paper) -> String`, `targetUri(target) -> Uri` | 묻기 |
