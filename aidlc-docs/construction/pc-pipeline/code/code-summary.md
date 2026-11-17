# Code Summary — pc-pipeline

## 파일

| 파일 | 내용 | 규칙 |
| --- | --- | --- |
| `pipeline/radar/hf_client.py`, `retry.py` | 수집 · 재시도 · 방어적 해석 | BR-P02, BR-P03, NFR-P06 |
| `pipeline/radar/topics.py`, `select.py` | 키워드 규칙 분류 · 선별 | BR-P04, BR-P05 |
| `pipeline/radar/analyze.py`, `prompts/*.md` | none 결과, AI 분석, JSON 추출, 재요청 · 대체, 리포트 문장 | BR-P06 ~ BR-P10, BR-P17 |
| `pipeline/radar/providers.py` | none · anthropic · openai (호환) · gemini · ollama · cli | BR-P11, NFR-P01 |
| `pipeline/radar/publish.py` | 업로드 · 통계 조회 | BR-P12 |
| `pipeline/radar/runner.py` | 날짜 계획 · 하루 처리 · 상태 · 기록 · 리포트 | BR-P01, BR-P13 ~ BR-P18 |
| `pipeline/radar/config.py`, `cli.py` | 설정 · 비밀 · 명령 (`daily`, `report`, `check`, `token`) | NFR-P05, NFR-P07 |
| `pipeline/deploy/*` | launchd plist, 키체인 실행 스크립트, 설치 스크립트, 설정 예시 | infrastructure-design.md |
| `pipeline/uv.lock` | 의존성 잠금 | NFR-P09 |

## TDD 기록

| 단계 | 결과 |
| --- | --- |
| RED | 테스트 8개 파일 작성 후 실행: 구현 모듈이 없어 7개 파일 수집 오류 (ImportError). tdd-red 기준의 "AssertionError RED" 는 아니며, 미구현 확인 용도로만 기록 |
| GREEN | 83 통과 (계약 테스트 2개 포함: 서버 `DigestIngest` 로 직접 검사) |
| REFACTOR | ruff 정리, 쓰지 않는 형식 (`BriefResponse`) 제거, CLI 대역 처리 단순화. 83 통과 유지 |

## 실행 결과 (2026-11-17)

| 명령 | 결과 |
| --- | --- |
| `pytest --cov=radar` | 83 passed, 커버리지 94% |
| `ruff check`, `ruff format --check` | 통과 |
| `uv lock`, `uv run radar token · check · daily --help` | 동작 확인 |
| 실제 Hugging Face 호출 | 미실행: 이 세션의 셸에서 huggingface.co 접근이 막혀 있음. 응답 모양은 2026-11-17 에 웹 조회로 확인한 필드 이름으로 테스트 데이터를 만듦. 사용자 Mac 에서 `radar daily --dry-run out.json` 으로 확인 필요 |
| launchd 등록 | 미실행 (사용자 Mac 에서 `install-mac.sh`) |

## 설계와 다른 점 (CG-7)

- 계획에 없던 추가: `radar token` (토큰 · 해시 생성), `radar check --offline`, `--dry-run`, 수집 원본 보관 (`raw/{date}.json`)
- 결과 논문 순서는 Hugging Face 순서를 유지 (정렬은 서버 BR-S06 이 담당)
