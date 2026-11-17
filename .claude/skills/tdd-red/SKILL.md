---
name: tdd-red
description: TDD 1단계 (RED). 설계 문서 (업무 규칙 · NFR · 전이 표) 만 보고 실패하는 테스트를 작성하고, 사람 판정 후 테스트를 스냅샷으로 고정할 때 사용. "/tdd-red U1", "RED 테스트 작성", Code Generation 계획의 테스트 작성 Step 에 사용. 구현 · 버그 수정 (→ tdd-green), 구조 정리 (→ tdd-refactor) 에는 사용하지 않음.
---

# TDD RED: 설계 문서로 실패 테스트 작성

- 세션: 테스트 작성 전용 세션 (구현 세션과 분리)
- 인자: Unit 이름 (예: `U1`, `u1-auto-halt`)
- 공통 기준: `test-antipatterns.md` (같은 폴더, tdd-green · tdd-refactor 도 참조)
- git 을 쓰지 않음: 테스트 고정 · 변경 확인 · 되돌리기는 `tdd_snapshot.py` (같은 폴더) 로 함
- `<python>` = 공용 가상환경: Windows `..\.venv\Scripts\python.exe`, Mac `../.venv/bin/python` (실행 위치 = 모듈 폴더)

## 입력 (이것만 읽기)

- `aidlc-docs/construction/<unit>/functional-design/business-rules.md`
- `aidlc-docs/construction/<unit>/nfr-requirements/nfr-requirements.md`
- `docs/state-transitions.md`, `docs/api-todo.md`, `aidlc-docs/construction/plans/<unit>-code-generation-plan.md`
- 테스트 준비물: `tests/conftest.py` (fixture), 기존 `tests/` 의 호출 형식
- ⛔ 읽기 금지: `backend/` 구현 코드 본문 (Read 로 파일 열기 금지)
  - 문서에 없는 seam 이름 · 인자 · 외부 경계만 시그니처로 확인 (본문은 보지 않음)
    - `grep -rn "^def \|^async def \|@router\.\|@app\." backend/`
    - 외부 호출 · 대기 함수: `grep -rn "httpx\.\|time\.sleep" backend/services/`
  - DB 준비: `tests/conftest.py` fixture, `data/gen_seed.py` (테이블 정의 `CREATE TABLE` · seed 값, 읽기 허용)
  - 그래도 모르면 지어내지 말고 사람에게 질문

## 절차

1. 테스트 경계 (seam) 표 작성 → **사람 승인 대기**
   - 열: 규칙 ID · seam (API 경로 또는 서비스 함수) · 입력 · 기대값 · 테스트 파일
   - seam 은 공개 인터페이스만 (HTTP API, 문서에 적힌 서비스 함수)
   - 규칙 · 전이 표 1행 = 테스트 1개 (경계값은 `parametrize` 1개로 묶기)
2. 승인된 표대로 테스트 작성
   - 이름 = 동작 문장 (`test_halt_at_exactly_threshold`)
   - 첫 줄 주석 = 잡는 규칙: `# BR-03: 실패율 5.0% 에서 중단 (> 로 비교하면 실패)`
   - 기대값 = 문서의 숫자 · 상태 그대로 (리터럴), 코드처럼 계산하지 않기
   - mock 은 외부 경계만 (단말 mock 서버 · 시간), 직접 만든 모듈은 mock 금지
3. `<python> -m pytest <새 테스트 파일> -q` 실행 → 실패 사유 표 출력
   - 이 단계는 실패가 정상 (RED) → 전체 통과 · 커버리지 기준은 여기서 따지지 않음

   | 테스트 | 결과 | 실패 종류 | RED 인정 |
   | --- | --- | --- | --- |
   | `test_...` | FAILED | AssertionError (409 기대, 200) | ✅ |
   | `test_...` | ERROR | ImportError | ❌ 테스트 수정 필요 |

4. RED 판정
   - ✅ 인정: 기대값 비교 실패 (AssertionError, 상태 코드 · 상태 값 불일치), `backend/` 안에서 난 예외 (예: ZeroDivisionError = 제품 결함)
   - ❌ 불인정: 테스트 쪽 ImportError · NameError · fixture 오류 · 문법 오류 → 테스트를 고쳐 다시 3
   - 처음부터 통과하는 테스트: 회귀 보호용이면 표에 "보호" 로 표시, 아니면 기대값 재확인
5. **사람 판정 대기** ("RED 확인" 응답 전까지 고정 금지)
6. 테스트 고정 (스냅샷)
   - `<python> .claude/skills/tdd-red/tdd_snapshot.py lock <unit>`
   - 결과: `.lab/tdd/<unit>/red/` 에 `tests/` · `backend/` 복사 → 이후 단계가 이것과 비교
   - 고정 뒤 테스트를 고쳐야 하면 이 세션에서 고친 뒤 3 ~ 6 다시 (lock 을 다시 실행하면 덮어씀)

## 금지

- `backend/` 수정 · 열람, 테스트 skip · xfail
- 커버리지만 올리려는 테스트 (잡는 규칙 없는 테스트)
- 한 테스트에 규칙 여러 개 섞기
- git 명령 (commit · diff · checkout 등) 사용

## 완료 보고

- seam 표 (승인본), RED 판정 표, 고정 결과 (lock 출력 1줄)
- 다음 단계: 새 터미널에서 `claude` → `/tdd-green <unit>`
