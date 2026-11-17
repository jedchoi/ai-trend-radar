# NFR Requirements — mobile-app

| ID | 요구 | 측정 기준 | 출처 |
| --- | --- | --- | --- |
| NFR-A01 | 오프라인 | BR-A12. 저장본이 있으면 네트워크 없이 첫 화면 표시 (위젯 테스트) | FR-21 |
| NFR-A02 | 호환성 | 모든 모델 파싱이 모르는 필드 무시 · 선택 필드 없음 허용 (단위 테스트: 예시 응답 + 필드 추가 · 삭제 변형) | NFR-07 |
| NFR-A03 | 응답 시간 | HTTP 요청 시간 제한 10초, 저장본 표시 1초 이내 (위젯 테스트에서 첫 프레임 내 표시) | NFR-02 |
| NFR-A04 | 보안 | 앱에 비밀 없음 (토큰 · 키 없음), 외부 링크는 `http(s)` 만 열기, 서버 응답 문자열은 일반 텍스트로만 표시 (HTML 해석 없음) | NFR-04, SECURITY-05 |
| NFR-A05 | 접근성 | 텍스트 배율 1.3 에서 주요 화면 넘침 없음 (위젯 테스트), 아이콘 버튼에 tooltip | - |
| NFR-A06 | 테스트 | 모델 · 정렬 · 묻기 · 저장소 단위 테스트, 화면 6개 위젯 테스트 | NFR-06 |
| NFR-A07 | 공급망 | 패키지 3개 (`http`, `shared_preferences`, `url_launcher`) + 개발용 `flutter_lints`, `pubspec.lock` 커밋 | SECURITY-10 |

## Security Baseline 판정 (이 unit)

| 규칙 | 판정 | 근거 |
| --- | --- | --- |
| SECURITY-01 | compliant | 서버 주소 https 권장 · http 는 개발용 (Android 기본 정책상 http 차단, 설정 안내) |
| SECURITY-05 | compliant | 입력 (검색어 · 키워드 · 메모 · 주소) 길이 · 형식 제한 |
| SECURITY-10 | compliant | NFR-A07 |
| SECURITY-12 | compliant | 앱에 하드코딩 비밀 없음 |
| SECURITY-15 | compliant | 모든 요청 오류를 잡아 일반 안내로 표시 |
| SECURITY-02 ~ 04, 06 ~ 09, 11, 13, 14 | N/A | 서버 · 인증 · 웹 화면 없음 (읽기 전용 클라이언트) |
