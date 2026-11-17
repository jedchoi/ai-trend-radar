# Functional Design 계획 — mobile-app

## Question 1: 서버 주소가 없을 때
A) 데모 데이터 (앱에 포함한 예시 응답) 로 바로 둘러보게 한다
B) 설정 화면으로 보낸다

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 서버 배포 전에도 앱을 확인할 수 있다

## Question 2: 차트 구현
A) CustomPainter 로 직접 (패키지 없음)
B) 차트 패키지

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 막대 · 선 두 종류뿐이라 의존성을 늘리지 않음

## 실행 단계
- [x] business-rules.md (BR-A01 ~ BR-A13)
- [x] domain-entities.md
- [x] business-logic-model.md
- [x] frontend-components.md
