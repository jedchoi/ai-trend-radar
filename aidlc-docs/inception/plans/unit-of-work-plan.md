# Unit of Work 계획

## Question 1: unit 분해 기준
A) 배포 단위별 3개 (backend-server, pc-pipeline, mobile-app)
B) 하나의 unit
C) 기능 영역별 (수집, 분석, 조회, 앱 화면 ...)

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 실행 위치 (서버 · PC · 휴대폰) 와 언어가 다르다

## Question 2: 진행 순서
A) backend-server → pc-pipeline → mobile-app (API 계약을 먼저 고정)
B) pc-pipeline 먼저

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천)

## Question 3: 코드 구성
A) 단일 저장소 (monorepo): `server/`, `pipeline/`, `app/`, `contract/`
B) 저장소 3개

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 계약 변경을 한 커밋에서 세 곳에 반영

## 실행 단계
- [x] unit 정의 (unit-of-work.md)
- [x] unit 의존 관계 (unit-of-work-dependency.md)
- [x] story → unit 배정 (unit-of-work-story-map.md)
