# AI Trend Radar

매일 아침 6시, Hugging Face 의 AI 논문 · Hub 트렌드 · 블로그 뉴스를 내 PC 에서 수집 · AI 분석하고 (원문 포함), Docker 의 PostgreSQL 서버에 저장해 모바일 앱에서 보는 시스템.

```text
Hugging Face ──▶ PC 파이프라인 (pipeline/, 매일 06:00) ──업로드──▶ backend 서버 (server/ + PostgreSQL, Docker) ◀──조회── 모바일 앱 (app/)
                 논문 · Hub · 뉴스 수집, 원문, AI 분석                저장 · 검색 · 트렌드 통계                     오늘 · 뉴스 · 트렌드 · 검색 · 보관함
```

## 처음 한 번 (내 Mac, Docker Desktop)

```sh
tool/radar-up.sh            # Postgres + API (Docker) → 지난 90일 채우기 (백그라운드) → 매일 06:00 등록 → 연결된 휴대폰에 앱 설치
tool/radar-up.sh --status   # 서버 · 일정 · 최근 실행
```

이미 쓰는 Postgres 가 있으면 `--database-url postgresql://user:pw@localhost:5432/radar`. 그 밖의 옵션은 `tool/radar-up.sh --help`. 다른 AI 도구로 이어서 작업할 때는 `aidlc-docs/handoff.md` 부터 읽는다.

| 폴더 | 내용 | 기술 |
| --- | --- | --- |
| `server/` | 업로드 (토큰) · 조회 · 검색 · 트렌드 · 뉴스 API | Python 3.12, FastAPI, PostgreSQL 16 (psycopg 3), Docker |
| `pipeline/` | 매일 수집 (논문 · Hub · 블로그 뉴스 · 원문) → 선별 → AI 분석 → 업로드, 주간 · 월간 리포트 | Python 3.11+, uv, httpx |
| `app/` | 오늘 · 뉴스 · 트렌드 · 검색 · 보관함 · 설정, 원문 보기 · 읽음 표시 · 글자 크기 | Flutter 3.41.7 |
| `contract/samples/` | API 예시 응답 (앱 테스트 입력) | 서버가 생성 |
| `deploy/local/` | Docker Desktop 용 Compose (Postgres + API), 06:00 launchd 일정 | |
| `deploy/server/` | 원격 서버용 Docker Compose (Postgres + API + Caddy HTTPS) | |
| `integration/` | 파이프라인 → 서버 통합 테스트 | |
| `aidlc-docs/` | AI-DLC 산출물 (요구사항 · 스토리 · 설계 · 감사 기록) | |

## AI 는 어디에 쓰나 — 다른 AI 로 바꾸기

AI 는 파이프라인의 분석 단계에서만 쓴다. `~/.config/ai-trend-radar/config.toml` 의 `[ai] provider` 한 줄로 바꾼다.

| provider | 필요한 것 | 비고 |
| --- | --- | --- |
| `none` | 없음 | Hugging Face 의 AI 요약 · 키워드 규칙. 구독 · 키 없이 전체 동작 |
| `anthropic` | API 키 | Claude API |
| `openai` | API 키 또는 `base_url` | OpenAI, 또는 LM Studio · vLLM · OpenRouter 같은 호환 서버 |
| `gemini` | API 키 | Google Gemini API |
| `ollama` | 로컬 Ollama | 내 PC 의 모델, 비용 없음 |
| `cli` | AI CLI 설치 · 로그인 | `command = ["claude", "-p"]`, `["gemini", "-p"]`, `["codex", "exec"]` 처럼 구독형 CLI 를 그대로 사용 |

프롬프트는 `pipeline/radar/prompts/*.md` 의 일반 텍스트라 어떤 모델에도 같은 형식을 요구한다. 서버와 앱은 어떤 AI 를 썼는지 알 필요가 없다. 트렌드 통계용 키워드는 Hugging Face 키워드를 쓰므로 AI 를 바꿔도 주간 비교가 흔들리지 않는다.

## 내 PC 에서 실제 데이터로 보기 (같은 Wi-Fi, http) — 나눠서 실행할 때

```sh
tool/radar-up.sh --server-only   # 서버만 (Docker: Postgres + API). 휴대폰에 넣을 주소 http://<PC IP>:8000 출력
tool/local-backfill.sh           # 지난 90일 실제 데이터 → 바로 업로드 → AI 분석 (최근 날부터) → 뉴스 → 주 · 월 리포트
tool/local-app.sh -d <기기>       # 앱을 이 서버 주소로 설치 · 실행 (profile 빌드)
tool/radar-daily.sh              # 어제 하루치 + 새 뉴스 (06:00 일정이 부르는 것과 같음)
tool/radar-up.sh --backup        # DB 백업 (.local/backups, pg_dump)
```

- 백필 1단계는 몇 분이면 끝나 앱에서 바로 볼 수 있고, AI 분석은 그 뒤에 최근 날부터 덮어쓴다. 오래 걸리면 끊었다가 다시 실행하면 이어서 한다
- 분석 AI 는 자동으로 고른다: `claude` CLI → `gemini` CLI → Ollama → 없음 (Hugging Face 요약). 바꾸려면 `.local/pipeline.toml` 의 `[ai]`
- Hub 트렌딩 (모델 · 데이터셋 · Spaces) 은 "지금" 목록만 받을 수 있어 백필의 마지막 날에만 붙는다. Hub 신규 · 체류 통계는 그날부터 쌓인다
- 뉴스는 Hugging Face 블로그 (RSS + 글 본문). 원문은 뉴스 본문 전체, 논문 초록, 주목 논문 본문, Hugging Face 응답 원본 JSON 을 저장한다
- 토큰 · 설정 · 로그는 저장소 안 `.local/` (git 제외), DB 는 Docker 볼륨 `radar-pg`. Android 는 debug · profile 빌드만 http 를 허용하고, release 빌드는 HTTPS 서버 (`deploy/server`) 가 필요하다

## 빠른 시작

1. **서버** (Linux 서버, Docker) — `deploy/server/README.md`
2. **PC 파이프라인** (Mac) — `pipeline/deploy/install-mac.sh` 실행 후 안내에 따라 토큰 · 키를 키체인에 저장
3. **앱** — `cd app && tool/bootstrap.sh && flutter run --dart-define=RADAR_SERVER_URL=https://<도메인>` (또는 앱 설정에서 주소 입력)

토큰은 PC 에서 `cd pipeline && uv run radar token` 으로 만든다. 출력의 `RADAR_INGEST_TOKEN` 은 PC 키체인에, `INGEST_TOKEN_SHA256` 은 서버 `.env` 에 넣는다.

## 점검

```sh
tool/check.sh              # 테스트 DB (Docker) → server · pipeline · 통합 · 예시 응답 동기화 · (flutter 가 있으면) app
tool/check.sh --skip-app   # TEST_DATABASE_URL 을 주면 그 Postgres 를 쓴다
```

CI (`.github/workflows/ci.yml`) 는 Postgres 서비스로 같은 점검을 하고, 성능 테스트, 의존성 취약점 검사, SBOM, Docker 이미지 (Postgres + API) 스모크 테스트, debug APK 빌드를 한다.

## 개발 방식

AI-DLC (`.aidlc-rule-details/`, `.claude/skills/aidlc*`) 로 진행했다. 인계 문서 `aidlc-docs/handoff.md`, 진행 상태 `aidlc-docs/aidlc-state.md`, 모든 결정과 입력 `aidlc-docs/audit.md`. 다른 AI 에이전트용 안내는 `AGENTS.md`.
