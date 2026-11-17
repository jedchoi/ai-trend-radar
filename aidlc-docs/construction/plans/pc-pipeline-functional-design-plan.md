# Functional Design 계획 — pc-pipeline

## Question 1: 트렌드용 키워드 출처
A) Hugging Face `ai_keywords` (제공자와 무관)
B) AI 가 뽑은 키워드

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). AI 를 바꿔도 키워드가 바뀌지 않아 주간 비교가 안정적

## Question 2: 구독형 CLI 지원
A) `cli` 제공자로 지원 (명령과 입력 방식을 설정)
B) API 만

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). API 키 없이 쓰던 AI 구독을 그대로 활용

## 실행 단계
- [x] business-rules.md (BR-P01 ~ BR-P18)
- [x] domain-entities.md
- [x] business-logic-model.md (PBT 속성)
- [x] frontend-components.md (N/A)
