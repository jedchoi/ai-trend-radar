# Application Design 계획

## Question 1: 트렌드 통계를 어디서 계산할까요?
A) 파이프라인 (PC) 이 계산해 올린다
B) 서버가 저장된 데이터로 계산하고, 파이프라인은 해석 문장만 올린다
C) 앱이 계산한다

X) Other (please describe after [Answer]: tag below)

[Answer]: B (사용자 위임 · AI 추천). 통계의 단일 출처를 서버로 두면 파이프라인을 바꾸거나 날짜를 다시 올려도 수치가 어긋나지 않는다

## Question 2: AI 호출 방식
A) 제공자별 SDK
B) 제공자별 HTTP API 직접 호출 (SDK 없음) + 구독형 CLI (claude · gemini · codex 등) 를 부르는 `cli` 제공자
C) LangChain 같은 통합 라이브러리

X) Other (please describe after [Answer]: tag below)

[Answer]: B (사용자 위임 · AI 추천). 의존성이 적고, 구독 CLI 도 쓸 수 있어 이식성 요구에 가장 맞다

## Question 3: 앱 상태 관리
A) Flutter 기본 ChangeNotifier + ListenableBuilder (추가 패키지 없음)
B) Riverpod
C) Bloc

X) Other (please describe after [Answer]: tag below)

[Answer]: A (사용자 위임 · AI 추천). 화면 수가 적고 읽기 위주라 기본 기능으로 충분, 의존성 최소화

## 실행 단계
- [x] 컴포넌트 식별 (components.md)
- [x] 컴포넌트 메서드 정의 (component-methods.md)
- [x] 서비스 · API 계약 정의 (services.md)
- [x] 의존 관계 정리 (component-dependency.md)
- [x] 통합 문서 작성 (application-design.md)
