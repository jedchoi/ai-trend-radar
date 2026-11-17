# 2주기 설계 (Functional · NFR · Infrastructure Design, 3 unit 공통)

근거: `inception/requirements/requirements.md` 2주기 (FR-23 ~ FR-31, NFR-10 ~ NFR-12), `inception/user-stories/stories.md` Epic F (US-21 ~ US-27).
승인: 사용자 위임 (audit.md 2026-11-17T16:20:00Z).

## 1. 계약 (contract) 추가 — 필드는 추가만 (NFR-07)

### 논문 (PaperIn 추가 필드)

| 필드 | 형식 | 규칙 |
| --- | --- | --- |
| `full_text` | 문자열 ≤ 200,000자, 선택 | 주목 논문의 본문 원문 — Hugging Face 논문 페이지 본문 (`/papers/{id}.md`, arXiv 원문을 HF 가 변환한 것) (BR-P31) |
| `source_raw` | JSON 객체 ≤ 100 KB, 선택 | Hugging Face Daily Papers 응답 원본 1건. 저장만 하고 응답에는 넣지 않는다 (BR-S31) |

응답 `Paper` 추가: `arxiv_url` (`https://arxiv.org/abs/{id}`), `has_full_text`. 일일 요약 (`/digests/*`) 의 논문은 `full_text = null` (응답 크기), 본문은 `/papers/{id}` 에서만 (BR-S32).

### 뉴스 (새 자원)

`NewsIn` (업로드) — `id` (`조직/슬러그` 또는 `슬러그`, 소문자 · 숫자 · `._-`), `url` (`https://huggingface.co/blog/...`), `title`, `published_at` (UTC 시각), `organization?`, `authors[] ≤ 30`, `image_url?`, `content` (원문 본문 ≤ 200,000자), `summary` (한국어 1~800자), `key_points[] ≤ 6` (각 ≤ 300자), `keywords[] ≤ 15`, `topic` (논문과 같은 9개), `summary_source` (`ai` · `abstract`), `source_raw?` (RSS 항목 원본)

| API | 설명 |
| --- | --- |
| `POST /api/v1/ingest/news` `{provider, items[≤20]}` | 토큰 필요. id 단위 덮어쓰기 (BR-S30). 응답 `{news: n}` |
| `GET /api/v1/news?q&topic&limit(1~50, 20)&offset(≤1000)` | 최신순 (`published_at` 내림차순, id 오름차순). 검색은 제목 · 요약 · 키워드 · 본문 (BR-S33). 응답 `{items: NewsBrief[], total}` |
| `GET /api/v1/news/{id}` | 원문 포함 전체. 없으면 404 |

`NewsBrief`: `id, title, url, published_at, organization, image_url, summary, topic, keywords`.

## 2. 업무 규칙

### backend-server
- **BR-S30** 뉴스 업로드는 한 트랜잭션. 같은 id 는 덮어쓰고 ingest_log 에 `news` 1행 (건수)
- **BR-S31** `source_raw` 는 JSONB 로 저장하고 어떤 공개 응답에도 넣지 않는다
- **BR-S32** 일일 요약 응답에는 본문 원문을 넣지 않는다. 논문 상세에만 `full_text`
- **BR-S33** 뉴스 검색은 BR-S10 과 같은 단어 분리 · 부분 일치 (AND)
- **BR-S34** 업로드 본문 최대 10 MB (NFR-11), 공개 응답은 기존 한도 유지
- **BR-S35** 데이터베이스는 `DATABASE_URL`. 시작할 때 DB 가 없으면 만들고 스키마를 만든다 (FR-23). 기존 SQLite 시절 열이 없던 스키마도 `ADD COLUMN IF NOT EXISTS` 로 맞춘다

### pc-pipeline
- **BR-P30** 뉴스 수집: RSS 를 읽어 `published_at` 이 기간 (일일 = 최근 3일, 백필 = `--days`) 안이고 아직 올리지 않은 글만 처리. 올린 id 는 `data_dir/news_seen.json` 에 기록 (같은 글은 한 번만 분석, FR-25)
- **BR-P31** 원문: 블로그 글은 본문 텍스트 (`blog-content` → `article` → `main` 순으로 찾고, nav · header · footer · script · style 제외). 주목 논문은 Hugging Face 논문 본문 (`https://huggingface.co/papers/{id}.md`, 없으면 비움) 을 `data/fulltext/{id}.md` 에 보관해 한 번만 받는다 (없던 것도 `.none` 으로 기록). 요청 사이 3초 (NFR-10), 실패는 원문만 비우고 계속
  - 구현 중 변경: 처음 설계는 arXiv HTML 이었으나, 1주기부터 쓰던 HF 논문 본문 경로가 같은 원문을 주고 호스트도 하나로 줄어 이것으로 바꿈 (요구 FR-26 은 그대로 충족)
- **BR-P32** 뉴스 분석: AI 가 있으면 NEWS 프롬프트로 `{summary, key_points, keywords, topic}`. 없거나 실패하면 본문 첫 문단 (최대 300자) 을 요약, 소제목 최대 5개를 핵심, `summary_source = abstract`, 주제는 topics.py 규칙 분류
- **BR-P33** 업로드는 10건씩 (NFR-11). 업로드 실패한 글은 seen 에 넣지 않는다 (다음 실행에서 재시도)
- **BR-P34** 일일 실행 순서: 논문 · Hub → 뉴스 → 리포트. 뉴스 실패는 일일 · 백필 결과를 실패로 만들지 않고 실행 기록에 `stage = news, status = failed` 로 남긴다. 백필은 같은 기간 (`--days`) 의 뉴스를 1단계 (논문 업로드) 직후 AI 없이 먼저 올리고, AI 단계가 끝난 뒤 AI 로 다시 분석해 덮어쓴다 (2026-11-18 수정: 처음에는 몇 시간 걸리는 AI 단계 뒤에 뉴스를 올려 앱의 뉴스가 비어 있었음). AI 없이 올린 글은 AI 제공자가 생기면 다시 분석해 덮어쓴다
- **BR-P35** 스케줄: launchd `StartCalendarInterval` 06:00 (Hour 6, Minute 0). 잠자기 중이면 깨어난 뒤 1회. 실행 셸은 `.local/` 의 설정 · 토큰 파일을 쓴다

### mobile-app
- **BR-A20** 서버 주소 우선순위: 사용자가 설정에서 저장한 값 > 빌드 시 `RADAR_SERVER_URL` > 없음 (설정 안내)
- **BR-A21** 하단 탭 5개: 오늘 · 뉴스 · 트렌드 · 검색 · 보관함. 설정은 오른쪽 위 (모든 탭)
- **BR-A22** 뉴스 목록은 20건씩, 끝에서 3건 남으면 다음 페이지. 당겨서 새로고침은 첫 페이지부터
- **BR-A23** 읽음: 상세를 연 논문 · 뉴스 id 를 기기에 저장 (최대 5,000개, 오래된 것부터 삭제), 목록에서 흐리게
- **BR-A24** 원문 보기: 논문 상세 = 초록 원문 (펼치기, 상세 요약이 없는 논문은 기존처럼 바로 표시) + "본문 원문 읽기" (긴 글이라 별도 화면에서 블록 단위로 그림) + arXiv 링크. 뉴스 상세 = 요약 · 핵심 · 키워드 다음에 본문 원문 전체. `## ` = 소제목, `- ` = 항목. 길게 눌러 복사
- **BR-A25** 글자 크기: 설정에서 0.9 · 1.0 · 1.15 · 1.3 배, 앱 전체 `TextScaler` 에 적용
- **BR-A26** 보관함은 논문과 뉴스를 함께 담는다 (종류 표시, 저장 키: 논문 = id, 뉴스 = `news:` + id — 1주기 저장본과 호환). 공유 = 제목 + 링크 복사
- **BR-A28** 원문이 든 큰 응답 (30만 자 초과) 은 오프라인 저장본에 넣지 않는다 (기기 저장소 보호)
- **BR-A27** 오늘 화면 맨 위에 최신 뉴스 3건 (가로 카드)

## 3. 인프라

| 구성 | 로컬 (Docker Desktop) | 운영 |
| --- | --- | --- |
| Postgres | `deploy/local/compose.yml` 의 `db` (postgres:16-alpine, 볼륨 `radar-pg`, 포트 127.0.0.1:5433) — `--database-url` 을 주면 띄우지 않음 | `deploy/server/docker-compose.yml` 의 `db` (내부망만) |
| API | `api` (server/Dockerfile), 포트 0.0.0.0:8000 (같은 Wi-Fi 휴대폰) | `api` + Caddy HTTPS |
| 비밀 | `.local/.env` (권한 600): `POSTGRES_PASSWORD`, `DATABASE_URL`, `INGEST_TOKEN_SHA256` | `deploy/server/.env` |
| 파이프라인 | PC 의 uv 환경, launchd 06:00 | 같음 |
| 백업 | `tool/radar-up.sh --backup` → `pg_dump` | `deploy/server/backup.sh` (`pg_dump -Fc`, 30일) |

`localhost` · `127.0.0.1` 이 든 기존 Postgres 주소는 컨테이너 안에서 `host.docker.internal` 로 바꿔 쓴다.

## 4. 테스트 계획 (TDD)

| 대상 | 테스트 |
| --- | --- |
| server | `tests/test_news.py` (BR-S30 ~ S34), `tests/test_original_text.py` (full_text · source_raw · arxiv_url), 실제 Postgres |
| pipeline | `tests/test_news.py` (RSS 파싱, 본문 추출, 기간 · seen 필터, AI/없음 분석, 10건 분할, 실패 시 seen 미기록), `tests/test_fulltext.py` (HF 본문 보관, 3초 간격, 실패 무시, 원본 JSON), 실행 스크립트는 리허설 (아래 Build and Test) |
| integration | 가짜 HF (블로그 · arXiv 포함) → 파이프라인 → 실제 서버 (Postgres) → 뉴스 · 원문 조회 |
| app | `test/cycle2_test.dart` (뉴스 · 원문 파싱, 원문 블록, 읽음, 글자 크기, 기본 서버 주소, 보관함 뉴스), `test/widget_test.dart` 2주기 6개 (소식 카드 → 뉴스 탭, 뉴스 상세 · 보관 · 읽음, 뉴스 검색, 논문 원문, 읽음 표시, 글자 크기) |
