---
name: tdd-refactor
description: TDD 3단계 (REFACTOR). GREEN 상태에서 동작을 바꾸지 않고 중복 · 흩어진 규칙을 정리할 때 사용. "/tdd-refactor U1", "리팩토링", Code Generation 계획의 Refactor Step 에 사용. 새 기능 · 버그 수정 (→ tdd-green), 테스트 작성 (→ tdd-red) 에는 사용하지 않음.
---

# TDD REFACTOR: 동작은 그대로, 구조만 정리

- 세션: GREEN 을 끝낸 구현 세션 그대로
- 인자: Unit 이름 (예: `/tdd-refactor U1`)
- 기준: 테스트가 곧 동작 명세 → 테스트 변경 0, 결과 동일
- git 을 쓰지 않음: 변경 확인 · 되돌리기는 `.claude/skills/tdd-red/tdd_snapshot.py` (아래 `<snapshot>`) 로 함
- `<python>` = 공용 가상환경: Windows `..\.venv\Scripts\python.exe`, Mac `../.venv/bin/python` (실행 위치 = 모듈 폴더)
- `<snapshot>` = `<python> .claude/skills/tdd-red/tdd_snapshot.py`

## 검증 명령 (변경 1건마다 직접 실행)

1. `<python> -m ruff check .`
2. `<python> -m pytest -q --cov=backend.services --cov-fail-under=80 --cov-report=term`

## 시작 확인

1. 검증 명령 2개 통과 (GREEN) 인지 → 실패가 있으면 중단 (tdd-green 으로 돌아가기)
2. `<snapshot> check <unit>` → 종료 코드 0 (테스트가 RED 고정본과 같음)
3. GREEN 저장본 확인: `.lab/tdd/<unit>/green/` 이 없으면 `<snapshot> save <unit>` 실행
4. 기준 커버리지 기록: 검증 명령 2 출력의 TOTAL %

## 대상 고르기 (후보 표 → 사람 승인)

- 기준 문서: `docs/state-transitions.md`, 업무 규칙, AGENTS.md 4 · 6절
- 후보 찾는 곳: 이번 Unit 에서 바꾼 파일 (`<snapshot> changed <unit>`)
- 후보 종류
  - 같은 규칙이 2곳 이상 (예: 전이 규칙 `main.ALLOWED` · `rollout_service.TRANSITIONS`, `advance` 의 if 문 단계 순서)
  - 문서 표와 코드 구조가 다른 곳 (표 1개 → 코드 표 1개로)
  - GREEN 때 급하게 넣은 중복 · 긴 함수 · 의미 없는 이름

| 후보 | 위치 | 이유 (기준 문서) | 동작 변화 위험 |
| --- | --- | --- | --- |
| 단계 순서 if 문 → 표 | `main.advance_rollout` | 전이 표 1곳 기준 | 낮음 |

- **사람 승인 대기**, 정리할 것이 없으면 "대상 없음" 으로 보고 후 종료 (정상 결과)

## 절차 (후보 1개씩)

1. 바꾸기 전 범위 선언: 파일 · 함수, 바뀌지 않는 것 (API 응답 · 상태 코드 · 로그 문구)
2. 한 번에 하나만 변경 (이름 바꾸기 · 표로 옮기기 · 함수 추출 중 1가지)
3. 검증 명령 실행
   - 실패: 바로 되돌리기 (`<snapshot> revert <unit>` = `backend/` 를 마지막 저장본으로), 원인 보고
   - 통과: `<snapshot> save <unit>` 으로 저장본 갱신 (다음 후보의 되돌리기 기준)
4. 다음 후보

## 금지

- 동작 추가 · 수정 (새 상태 · 새 응답 필드 · 오류 문구 변경), 버그 발견 시 기록만 하고 tdd-red 로 넘기기
- 테스트 수정 · 추가 (테스트 정리도 이번 단계 범위 밖)
- 승인 안 된 파일 · Unit 밖 코드 정리
- 레거시 이상 동작 정리 (예: DRAFT 에서 바로 start 허용) → 동작 변화라 별도 요구로 보고
- git 명령 (commit · diff · checkout 등) 사용

## 완료 확인

1. 검증 명령 2개 통과
2. `<snapshot> check <unit>` → 종료 코드 0 (테스트 변경 없음)
3. 커버리지 = 시작 기록 이상

## (선택) 독립 리뷰 관점

- 새 세션에 업무 규칙 · AC · 바뀐 파일 목록 (`<snapshot> changed <unit>`) 만 전달 → 아래 확인
  - 테스트가 규칙을 잡는가 (`../tdd-red/test-antipatterns.md` 1 ~ 4)
  - 구현이 테스트 입력에만 맞춘 하드코딩인가
  - 문서 표와 코드 표가 1:1 인가

## 완료 보고

- 정리한 후보 · 건너뛴 후보 (이유), 테스트 수 · 커버리지 전후, 테스트 변경 확인 결과 (종료 코드)
