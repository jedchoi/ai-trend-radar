# Functional Design 계획 — backend-server

## Question 1: 급상승 키워드 기준
A) 직전 4개 기간 평균 대비 2배 이상, 기간 편수 3 이상
B) 직전 1개 기간 대비
C) 절대 편수 상위

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 기획서의 "직전 4주 평균" 과 일치, 한 주 변동에 덜 흔들림

## Question 2: 검색 방식
A) SQLite FTS5 (접두어 일치, AND)
B) LIKE 부분 일치
C) 외부 검색 엔진

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 1만 건 기준 NFR-02 충족, 추가 서버 없음

## 실행 단계
- [x] domain-entities.md
- [x] business-rules.md (BR-S01 ~ BR-S22)
- [x] business-logic-model.md (PBT 속성 포함)
- [x] frontend-components.md (N/A 근거)
