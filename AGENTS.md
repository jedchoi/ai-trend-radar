# AGENTS.md

AI 코딩 에이전트 (Claude Code, Codex CLI, Gemini CLI, Cursor 등) 공통 안내. 도구별 파일 (`CLAUDE.md`, `GEMINI.md`) 은 이 파일을 가리킨다.

**이어서 작업할 때 먼저 읽기: `aidlc-docs/handoff.md`** (현재 상태 · 실행 방법 · 규칙 · 결정 이유 · 다음 할 일)

## 명령

```sh
tool/check.sh                                   # 전체 점검 (CI 와 같음, 테스트 Postgres 는 tool/test-db.sh 로 자동)
tool/radar-up.sh                                # Docker Desktop: Postgres + API → 90일 채우기 → 06:00 일정 → 앱 설치
tool/radar-up.sh --server-only | --status | --logs | --stop | --backup | --psql
tool/radar-daily.sh                             # 06:00 일정이 부르는 실행 (어제 + 빠진 날 + 새 뉴스 + 리포트)
tool/test-db.sh [--stop]                        # 테스트용 Postgres (127.0.0.1:55432, 메모리)
tool/local-backfill.sh [--days 90]              # 로컬 서버에 지난 N 일 실제 데이터 (radar backfill)
tool/local-pipeline.sh                          # 로컬 서버로 어제 하루치
tool/local-app.sh -d <기기>                     # 로컬 서버 주소로 앱 설치 · 실행
cd server && .venv/bin/pytest -q                # 서버 테스트 (Postgres 필요: TEST_DATABASE_URL, 성능: -m perf)
cd pipeline && uv run pytest -q                 # 파이프라인 테스트
PYTHONPATH=server:pipeline pytest integration   # 통합
cd app && flutter test                          # 앱
cd server && python -m tools.make_samples       # 계약 예시 갱신 (앱 테스트 입력, SAMPLES_DATABASE_URL 의 DB 를 비우고 씀)
```

## 구조 규칙

- 세 unit 을 잇는 계약은 서버 API 하나다. 정본 = `server/app/schemas.py`. 필드는 추가만 한다 (`/api/v1`). 바꾸면 `pipeline/radar/models.py` · `pipeline/radar/news.py`, `app/lib/models/`, `contract/samples/` 를 같은 커밋에서 맞춘다 (`pipeline/tests/test_contract.py` · `test_news.py`, CI 의 samples diff 가 검사)
- 저장소는 PostgreSQL (`server/app/repository.py`, psycopg 3). 스키마는 시작할 때 `CREATE ... IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` 로 맞춘다 (마이그레이션 도구 없음, 열은 추가만)
- AI 호출은 `pipeline/radar/providers.py` 의 `complete(system, user) -> str` 하나로만 한다. 프롬프트는 `pipeline/radar/prompts/*.md` (첫 줄 = 작업 이름, `---USER---` 아래 = 사용자 메시지 틀)
- 트렌드 통계는 서버가 계산한다 (`server/app/trends.py`). 파이프라인은 해석 문장만 올린다
- 비밀 (업로드 토큰, AI 키) 은 저장소 · 설정 파일 · 로그에 두지 않는다. PC = 키체인, 서버 = `.env` 의 토큰 해시

## 개발 절차 (AI-DLC)

- 규칙: `.aidlc-rule-details/core-workflow.md` 부터. stage 스킬: `.claude/skills/aidlc*/SKILL.md` (일반 Markdown 이라 다른 에이전트도 그대로 읽을 수 있다)
- 상태: `aidlc-docs/aidlc-state.md`, 감사 기록: `aidlc-docs/audit.md` (덧붙이기만)
- 새 기능은 Requirements Analysis 부터 다시 (다음 주기 후보: 푸시 알림, 밀린 날 따라잡기, 모델 · 조직 팔로우, 듣기 모드). 2주기 설계는 `aidlc-docs/construction/cycle2-design.md`
