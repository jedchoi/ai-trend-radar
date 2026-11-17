# 요구사항 확인 질문 (Requirement Verification Questions)

> 모든 답은 AI 추천값이다. 사용자가 "모두 너의 추천으로 진행하고 멈추지말고 진행해" 로 결정을 위임했다 (audit.md 2026-11-17T12:56:49Z).

## Question 1: 분석에 쓸 AI
매일 요약 · 분류에 어떤 AI 를 쓸까요?

A) 특정 제공자 하나로 고정
B) 제공자 교체 가능 구조: 키 없이 도는 `none` (Hugging Face 요약 재사용) + Anthropic · OpenAI 호환 · Gemini · Ollama (로컬) 중 설정으로 선택
C) 로컬 모델만

X) Other (please describe after [Answer]: tag below)

[Answer]: B (사용자 위임 · AI 추천). 구독 · 키가 없어도 동작해야 한다는 사용자 요구 (이식성) 를 직접 만족

## Question 2: 호스팅 서버 형태
PC 분석 결과를 앱에 내줄 서버는?

A) 정적 파일 호스팅 (JSON 파일)
B) backend 서버 (FastAPI + SQLite): 저장 · 조회 · 검색 · 트렌드 통계 API, Docker 배포
C) 관리형 BaaS (Firebase, Supabase)

X) Other (please describe after [Answer]: tag below)

[Answer]: B (사용자 위임 · AI 추천). 사용자가 "backend 서버" 를 기대, 검색 · 트렌드 통계를 서버에서 계산 가능. 사용자가 이미 FastAPI + Docker 로 Oracle 서버를 운영 중 (iworship)

## Question 3: 모바일 앱 기술
A) Flutter (Android 우선, iOS 는 같은 코드)
B) 네이티브 Android (Kotlin)
C) React Native

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 사용자가 TidalConnect · iworship 에서 Flutter 사용 중

## Question 4: 첫 주기 앱 기능 범위
A) 세 화면만 (뉴스 리스트, 뉴스 요약, 트렌드 분석)
B) 세 화면 + 검색, 보관함 (북마크 · 상태 · 메모), 관심 키워드 맞춤 정렬, 적용 관점 요약, 바로 써보기 링크, 용어 카드, 관련 이전 논문, AI 에게 이어서 묻기
C) B + 푸시 알림 · 듣기 모드

X) Other (please describe after [Answer]: tag below)

[Answer]: B (사용자 위임 · AI 추천). 푸시는 푸시 서비스 계정 · 기기 토큰 관리가 필요해 다음 주기로

## Question 5: PC 실행 방식
A) macOS launchd 예약 실행 (매일 08:00 KST) + 누락일 자동 채우기
B) 사용자가 수동 실행
C) 서버에서 수집까지 실행

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 사용자 요구 "현재 pc 에서 가져와서 분석"

## Question 6: 요약 언어
A) 한국어 요약, 논문 제목 · 고유명사는 원문
B) 영어
C) 둘 다

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천)

## Question 7: 사용자 · 인증
A) 개인 사용 (본인 1인). 앱 조회는 로그인 없음, PC → 서버 업로드만 토큰 인증
B) 여러 사용자 계정

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 보관함 · 관심 키워드는 기기 안에 저장

## Question: 보안 확장 (Security Extensions)
이 프로젝트에 보안 확장 규칙을 강제할까요?

A) 예 — 모든 SECURITY 규칙을 차단성 제약으로 강제 (운영 수준 애플리케이션에 권장)

B) 아니요 — 모든 SECURITY 규칙 건너뜀 (PoC, 프로토타입, 실험 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 인터넷에 공개되는 서버와 업로드 토큰 · AI API 키를 다루므로 적용. 사용자 계정이 없어 비밀번호 · MFA · 세션 규칙은 N/A 로 판정

## Question: 복원력 확장 (Resiliency Extensions)
이 프로젝트에 복원력 기준 (resiliency baseline) 을 적용할까요?

A) 예 — 복원력 기준을 방향 제시용 모범 사례 및 설계 단계 지침으로 적용
B) 아니오 — 복원력 기준 생략

X) Other (please describe after [Answer]: tag below)

[Answer]: B (사용자 위임 · AI 추천). 개인용 단일 서버. 실패 시 기존 데이터 유지 · 누락일 채우기는 NFR-03 로 따로 다룸

## Question: 속성 기반 테스트 확장 (Property-Based Testing Extension)
이 프로젝트에 속성 기반 테스트 (PBT) 규칙을 강제할까요?

A) 예 — 모든 PBT 규칙을 차단성 제약으로 강제
B) 부분 — 순수 함수와 직렬화 왕복 (round-trip) 에만 PBT 규칙 강제
C) 아니요 — 모든 PBT 규칙 건너뜀

X) Other (please describe after [Answer]: tag below)

[Answer]: B (사용자 위임 · AI 추천). 선별 점수 · 트렌드 계산 · JSON 직렬화 왕복이 순수 함수
