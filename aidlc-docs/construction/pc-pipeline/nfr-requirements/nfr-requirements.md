# NFR Requirements — pc-pipeline

| ID | 요구 | 측정 기준 | 출처 |
| --- | --- | --- | --- |
| NFR-P01 | 이식성 | 제공자 6종 (none, anthropic, openai, gemini, ollama, cli) 이 같은 인터페이스. 프롬프트는 제공자와 무관한 파일. `none` 으로 전체 흐름 자동 테스트 통과 | NFR-01 |
| NFR-P02 | 비용 상한 | AI 대상 최대 `max_ai_papers` 편, 한 날짜 AI 호출 수 ≤ ceil(n/10) + 주목 수 + 1 (+ 재시도) | NFR-05 |
| NFR-P03 | 실행 시간 | `none`: 수집 제외 2분 이내 (자동 테스트 1초 이내). 외부 호출마다 시간 제한 (HF 30초, AI `timeout_s` 기본 120초) | NFR-08 |
| NFR-P04 | 실패 격리 | BR-P18. 업로드 전 계약 검사 | NFR-03 |
| NFR-P05 | 비밀 관리 | 토큰 · API 키는 환경 변수 또는 권한 600 파일, 로그 · 실행 기록 · 원본 보관 파일에 기록 안 함. 설정 파일에는 변수 이름만 | NFR-04, SECURITY-12 |
| NFR-P06 | 신뢰할 수 없는 입력 | HF 응답 · AI 응답은 Pydantic 으로 검사 후 사용, 형식 위반은 버림 · 대체 | SECURITY-05, 13 |
| NFR-P07 | 전송 | 서버 주소는 `https://` 만 허용 (`http://localhost` · `127.0.0.1` 은 테스트용 예외) | SECURITY-01 |
| NFR-P08 | 테스트 | 라인 커버리지 80% 이상, PBT (부분), 외부 HTTP 는 MockTransport 로만 대체 | NFR-06 |
| NFR-P09 | 공급망 | 의존성 고정 (`uv.lock`), CI `pip-audit` | SECURITY-10 |

## Security Baseline 판정 (이 unit)

| 규칙 | 판정 | 근거 |
| --- | --- | --- |
| SECURITY-01 | compliant | NFR-P07 |
| SECURITY-03 | compliant | 실행 기록 (BR-P16), 비밀 미기록 |
| SECURITY-05, 13 | compliant | NFR-P06 |
| SECURITY-10 | compliant | NFR-P09 |
| SECURITY-12 | compliant (하드코딩 금지) / N/A (계정 · 세션) | NFR-P05 |
| SECURITY-15 | compliant | 외부 호출 시간 제한 · 예외 처리 · 실패 시 업로드 안 함 (닫힌 실패) |
| SECURITY-02, 04, 06 ~ 09, 11, 14 | N/A | 네트워크 서비스를 열지 않는 명령줄 도구 |
