# AGENTS.md

AI 코딩 에이전트 (Claude Code, Codex CLI, Gemini CLI, Cursor 등) 공통 안내. 도구별 파일 (`CLAUDE.md`, `GEMINI.md`) 은 이 파일을 가리킨다.

## 명령

```sh
tool/check.sh                                   # 전체 점검 (CI 와 같음)
cd server && .venv/bin/pytest -q                # 서버 테스트 (성능: -m perf)
cd pipeline && uv run pytest -q                 # 파이프라인 테스트
PYTHONPATH=server:pipeline pytest integration   # 통합
cd app && flutter test                          # 앱
cd server && python -m tools.make_samples && cp ../contract/samples/*.json ../app/assets/demo/   # 계약 예시 갱신
```

## 구조 규칙

- 세 unit 을 잇는 계약은 서버 API 하나다. 정본 = `server/app/schemas.py`. 필드는 추가만 한다 (`/api/v1`). 바꾸면 `pipeline/radar/models.py`, `app/lib/models/models.dart`, `contract/samples/`, `app/assets/demo/` 를 같은 커밋에서 맞춘다 (`pipeline/tests/test_contract.py`, CI 의 samples diff 가 검사)
- AI 호출은 `pipeline/radar/providers.py` 의 `complete(system, user) -> str` 하나로만 한다. 프롬프트는 `pipeline/radar/prompts/*.md` (첫 줄 = 작업 이름, `---USER---` 아래 = 사용자 메시지 틀)
- 트렌드 통계는 서버가 계산한다 (`server/app/trends.py`). 파이프라인은 해석 문장만 올린다
- 비밀 (업로드 토큰, AI 키) 은 저장소 · 설정 파일 · 로그에 두지 않는다. PC = 키체인, 서버 = `.env` 의 토큰 해시

## 개발 절차 (AI-DLC)

- 규칙: `.aidlc-rule-details/core-workflow.md` 부터. stage 스킬: `.claude/skills/aidlc*/SKILL.md` (일반 Markdown 이라 다른 에이전트도 그대로 읽을 수 있다)
- 상태: `aidlc-docs/aidlc-state.md`, 감사 기록: `aidlc-docs/audit.md` (덧붙이기만)
- 새 기능은 Requirements Analysis 부터 다시 (다음 주기 후보: 푸시 알림, 밀린 날 따라잡기, 모델 · 조직 팔로우, 듣기 모드)
