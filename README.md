# AI Trend Radar

매일 Hugging Face 의 AI 논문 · Hub 트렌드를 내 PC 에서 수집 · 분석하고, backend 서버에 올려 모바일 앱에서 보는 시스템.

```text
Hugging Face ──▶ PC 파이프라인 (pipeline/) ──HTTPS 업로드──▶ backend 서버 (server/) ◀──HTTPS 조회── 모바일 앱 (app/)
                 수집 · AI 분석 · 리포트                      저장 · 검색 · 트렌드 통계               뉴스 · 요약 · 트렌드
```

| 폴더 | 내용 | 기술 |
| --- | --- | --- |
| `server/` | 업로드 (토큰) · 조회 · 검색 · 트렌드 API | Python 3.12, FastAPI, SQLite (FTS5), Docker |
| `pipeline/` | 매일 수집 → 선별 → AI 분석 → 업로드, 주간 · 월간 리포트 | Python 3.11+, uv, httpx |
| `app/` | 오늘 · 트렌드 · 검색 · 보관함 · 설정 | Flutter 3.41.7 |
| `contract/samples/` | API 예시 응답 (앱 데모 · 테스트 입력) | 서버가 생성 |
| `deploy/server/` | Docker Compose + Caddy (HTTPS) | |
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

## 내 PC 에서 서버 띄우고 휴대폰으로 보기 (같은 Wi-Fi, http)

```sh
tool/local-server.sh --demo        # 서버 시작, 휴대폰에 넣을 주소 (http://<PC IP>:8000) 를 출력. --demo = 예시 데이터
tool/local-pipeline.sh             # (다른 터미널) 어제 Hugging Face 데이터를 수집해 로컬 서버에 업로드
cd app && tool/bootstrap.sh && flutter run --profile   # 앱 설정 > 서버 주소에 위 주소 입력
```

토큰 · DB · 설정은 저장소 안 `.local/` (git 제외) 에 만들어진다. Android 는 debug · profile 빌드만 http 를 허용하고, release 빌드는 HTTPS 서버 (`deploy/server`) 가 필요하다.

## 빠른 시작

1. **서버** (Linux 서버, Docker) — `deploy/server/README.md`
2. **PC 파이프라인** (Mac) — `pipeline/deploy/install-mac.sh` 실행 후 안내에 따라 토큰 · 키를 키체인에 저장
3. **앱** — `cd app && tool/bootstrap.sh && flutter run` (서버 주소가 없으면 데모 데이터로 실행)

토큰은 PC 에서 `cd pipeline && uv run radar token` 으로 만든다. 출력의 `RADAR_INGEST_TOKEN` 은 PC 키체인에, `INGEST_TOKEN_SHA256` 은 서버 `.env` 에 넣는다.

## 점검

```sh
tool/check.sh              # server · pipeline · 통합 · 예시 응답 동기화 · (flutter 가 있으면) app
tool/check.sh --skip-app
```

CI (`.github/workflows/ci.yml`) 는 같은 점검에 더해 성능 테스트, 의존성 취약점 검사, SBOM, Docker 이미지 스모크 테스트, 데모 APK 빌드를 한다.

## 개발 방식

AI-DLC (`.aidlc-rule-details/`, `.claude/skills/aidlc*`) 로 진행했다. 진행 상태는 `aidlc-docs/aidlc-state.md`, 모든 결정과 입력은 `aidlc-docs/audit.md`. 다른 AI 에이전트용 안내는 `AGENTS.md`.
