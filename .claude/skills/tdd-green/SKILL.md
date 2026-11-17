---
name: tdd-green
description: TDD 2단계 (GREEN). tdd-red 가 스냅샷으로 고정한 테스트를 고치지 않고 최소 구현으로 통과시킬 때 사용. "/tdd-green U1", "GREEN 구현", Code Generation 계획의 구현 Step 에 사용. 테스트 작성 (→ tdd-red), 동작을 바꾸지 않는 구조 정리 (→ tdd-refactor) 에는 사용하지 않음.
---

# TDD GREEN: 고정된 테스트를 최소 구현으로 통과

- 세션: 구현 전용 새 세션 (테스트 작성 세션과 분리)
- 인자: Unit 이름 (예: `/tdd-green U1`)
- 테스트 판단 기준: `../tdd-red/test-antipatterns.md`
- git 을 쓰지 않음: 테스트 변경 확인 · 되돌리기는 `.claude/skills/tdd-red/tdd_snapshot.py` (아래 `<snapshot>`) 로 함
- `<python>` = 공용 가상환경: Windows `..\.venv\Scripts\python.exe`, Mac `../.venv/bin/python` (실행 위치 = 모듈 폴더)
- `<snapshot>` = `<python> .claude/skills/tdd-red/tdd_snapshot.py`

## 검증 명령 (수정할 때마다 직접 실행)

1. `<python> -m ruff check .`
2. `<python> -m pytest -q --cov=backend.services --cov-fail-under=80 --cov-report=term`

- 자동 실행 장치에 기대지 않음: 파일을 고친 뒤 이 2개를 직접 돌리고 출력으로 판단

## 시작 확인

1. `<snapshot> check <unit>` → 종료 코드 0 (`tests/` 가 RED 고정본과 같음)
   - "RED 스냅샷 없음" 이면 중단 → tdd-red 를 먼저 끝내도록 안내
   - 종료 코드 1 (테스트가 고정본과 다름) 이면 중단 → 바뀐 파일을 보고하고 사람에게 질문
2. 전체 `<python> -m pytest -q` → 실패 목록 = 이번 구현 대상 (표로 출력)
3. 입력: Code Generation 계획 · 업무 규칙 · NFR 설계, 실패 테스트 (`tests/` 는 읽기만)

## 절차

1. 실패 테스트 1개 (또는 같은 규칙 묶음) 선택
2. 계획에 적힌 파일 범위 안에서 통과할 만큼만 구현
   - 계획 밖 파일 · 요청 없는 기능 추가 금지
   - 새 API 는 `/add-endpoint` 절차 (라우터 파일 위치 · 형식) 참고
3. 검증 명령 실행 → 실패 원인 수정 → 반복
   - pytest 는 전체 테스트를 돌림: 다른 테스트가 깨지면 그것부터 복구
4. 실패 목록이 빌 때까지 1 ~ 3 반복
5. 테스트가 이상하다고 판단되면 **고치지 말고 중단**
   - 보고: 테스트 이름 · 문서와 다른 점 · 근거 (규칙 ID)
   - 사람이 tdd-red 세션에서 수정 후 다시 고정 (lock) → `/tdd-green <unit>` 다시 시작

## 금지 (자주 나오는 핑계와 답)

| 핑계 | 답 |
| --- | --- |
| "테스트 기대값만 조금 고치면 된다" | 테스트 수정 금지, 보고 후 중단 |
| "이 테스트는 지금 범위가 아니라 skip" | skip · xfail · 삭제 금지 |
| "테스트 입력일 때만 이 값 반환" | 기대값 맞추기용 하드코딩 금지 (규칙대로 구현) |
| "커버리지가 모자라니 테스트 추가" | 테스트 추가는 tdd-red 세션만, 부족분은 보고 |
| "문서와 다르니 테스트 밖 규칙도 같이 맞춤" | 실패 테스트가 요구한 만큼만, 나머지 차이는 보고 (다음 RED 소재) |
| "git 으로 확인 · 되돌리면 빠르다" | git 명령 금지, `<snapshot>` 만 사용 |

## 완료 확인

1. 검증 명령 2개 통과 (ruff 지적 0, 전체 테스트 통과, 커버리지 80% 이상), 경고 · 오류 출력 0
2. `<snapshot> check <unit>` → 종료 코드 0 (테스트 변경 없음)
   - 0 이 아니면 `<snapshot> restore <unit>` 으로 테스트를 되돌리고 다시 1
3. GREEN 저장: `<snapshot> save <unit>` (`.lab/tdd/<unit>/green/` 에 `backend/` 복사, 리팩토링 되돌리기 기준)

## 완료 보고

- 바꾼 파일 목록 (`<snapshot> changed <unit>` 출력), 통과한 테스트 수, 커버리지, 테스트 변경 확인 결과 (종료 코드)
- 화면에서 확인할 위치 1줄 (예: 🚧 카드 사라짐)
- 다음 단계: 같은 세션에서 `/tdd-refactor <unit>`
