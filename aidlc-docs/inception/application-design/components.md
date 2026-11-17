# 컴포넌트 (Components)

## backend-server (`server/`)

| ID | 컴포넌트 | 위치 | 책임 | Story |
| --- | --- | --- | --- | --- |
| C-S1 | Public API Router | `server/app/routes_public.py` | 읽기 전용 조회 · 검색 · 트렌드 API | US-01 ~ US-03, US-05 ~ US-07, US-09 ~ US-12 |
| C-S2 | Ingest API Router | `server/app/routes_ingest.py` | 일일 요약 · 리포트 업로드 | US-19, US-20 |
| C-S3 | Ingest Auth | `server/app/security.py` | 업로드 토큰 검증 (해시 비교, 미설정 시 거부) | US-19 |
| C-S4 | Repository | `server/app/repository.py` | SQLite 저장 · 조회, FTS5 검색, 날짜 단위 트랜잭션 | US-01 ~ US-03, US-07, US-12, US-19 |
| C-S5 | Trend Service | `server/app/trends.py` | 주 · 월 통계, 급상승 키워드, Hub 신규 · 체류, 주제 시계열 | US-09 ~ US-11 |
| C-S6 | API Schemas | `server/app/schemas.py` | 요청 · 응답 형식 (API 계약), 입력 검증 | 전체 |
| C-S7 | Middleware | `server/app/middleware.py` | 요청 속도 제한, 보안 헤더, 접근 로그, 전역 오류 처리 | US-19, NFR-04 |

## pc-pipeline (`pipeline/radar/`)

| ID | 컴포넌트 | 위치 | 책임 | Story |
| --- | --- | --- | --- | --- |
| C-P1 | HF Client | `hf_client.py` | Daily Papers · 트렌딩 목록 · 논문 본문 수집, 재시도 | US-16 |
| C-P2 | Topic Rules | `topics.py` | 고정 주제 9개, 키워드 규칙 분류 | US-16, US-17 |
| C-P3 | Selector | `select.py` | 주목 논문 점수 · 선별 | US-16 |
| C-P4 | Analyzer | `analyze.py` | 프롬프트 구성, AI 응답 해석 · 검사 · 재시도 · 대체, 세 줄 요약 | US-16, US-17 |
| C-P5 | Providers | `providers.py` | none · anthropic · openai · gemini · ollama · cli | US-17 |
| C-P6 | Prompt Store | `prompts/*.md` | 제공자와 무관한 프롬프트 파일 | US-17 |
| C-P7 | Server Client | `publish.py` | 업로드 · 통계 조회 (토큰, 재시도) | US-19, US-20 |
| C-P8 | Runner | `runner.py` | 일일 실행, 누락일 채우기, 리포트, 실행 기록 | US-16, US-18, US-20 |
| C-P9 | Config · CLI | `config.py`, `cli.py` | TOML 설정, 비밀 읽기, 명령 (`radar daily` 등) | US-17, US-18 |
| C-P10 | Models | `models.py` | 업로드 형식 (서버 계약과 같은 필드), 검사 | US-17, US-19 |

## mobile-app (`app/lib/`)

| ID | 컴포넌트 | 위치 | 책임 | Story |
| --- | --- | --- | --- | --- |
| C-A1 | Api Client | `data/api_client.dart` | 서버 API 호출, JSON → 모델 | US-01 ~ US-03, US-05 ~ US-12 |
| C-A2 | Cache Store | `data/cache_store.dart` | 마지막 응답 저장 · 오프라인 제공 | US-14 |
| C-A3 | Settings Store | `data/settings_store.dart` | 서버 주소, 관심 키워드, 묻기 AI | US-04, US-08, US-15 |
| C-A4 | Library Store | `data/library_store.dart` | 북마크 · 상태 · 메모 | US-13 |
| C-A5 | Models | `models/*.dart` | Digest, Paper, Hub, Trend 모델 (모르는 필드 무시) | 전체 |
| C-A6 | Interest Ranker | `logic/interest_ranker.dart` | 관심 키워드 매칭 · 정렬 | US-04 |
| C-A7 | Ask Prompt Builder | `logic/ask_prompt.dart` | AI 에게 묻기 글 · 주소 | US-08 |
| C-A8 | Screens | `ui/screens/*.dart` | 오늘 · 논문 상세 · 트렌드 · 검색 · 보관함 · 설정 | US-01 ~ US-15 |
| C-A9 | Charts | `ui/widgets/charts.dart` | 막대 · 선 차트 (CustomPainter) | US-09, US-10 |
| C-A10 | App Controller | `state/*.dart` | 화면별 상태 (로딩 · 오류 · 오프라인) | 전체 |
