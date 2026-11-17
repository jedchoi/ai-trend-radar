# NFR Requirements — backend-server

| ID | 요구 | 측정 기준 | 출처 |
| --- | --- | --- | --- |
| NFR-S01 | 응답 성능 | 논문 10,000건 · Hub 3,600행 (6개월) 시드에서 `digests/latest`, `papers?q=`, `trends/weekly/latest`, `trends/series` 각각 100회 p95 300 ms 이하 (TestClient, 로컬) | NFR-02 |
| NFR-S02 | 실패 격리 | 업로드 중 예외 시 저장 0건 (테스트로 확인) | NFR-03 |
| NFR-S03 | 업로드 인증 | BR-S01. 토큰 원문은 서버에 저장하지 않고 SHA-256 만 환경 변수로 받음 | NFR-04, SECURITY-12 |
| NFR-S04 | 전송 암호화 | 외부 노출은 HTTPS 프록시 (Caddy) 만, 앱 컨테이너 포트는 외부에 열지 않음 | NFR-04, SECURITY-01 |
| NFR-S05 | 요청 속도 제한 | 공개 API IP 당 분당 120회, 업로드 분당 30회, 초과 429 | SECURITY-11 |
| NFR-S06 | 입력 검증 | 모든 경로 · 쿼리 · 본문에 타입 · 길이 · 형식 검사, 요청 본문 최대 2 MB, SQL 은 파라미터 바인딩만 | SECURITY-05 |
| NFR-S07 | 보안 헤더 | 모든 응답에 `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`. HSTS 는 프록시에서 | SECURITY-04 |
| NFR-S08 | 로깅 | 요청마다 JSON 한 줄 (시각, 요청 id, 메서드, 경로, 상태, 소요 ms, IP). 인증 실패 · 속도 제한은 `security_event` 로 기록. 토큰 · 본문은 기록하지 않음 | SECURITY-02, 03, 14 |
| NFR-S09 | 오류 응답 | 전역 오류 처리기, 응답은 `{"error": code}` 만 (스택 · 경로 · 버전 없음). `/docs` · `/openapi.json` 은 `ENABLE_DOCS=1` 일 때만 | SECURITY-09, 15 |
| NFR-S10 | 공급망 | 의존성 정확한 버전 고정, CI 에서 `pip-audit`, SBOM (CycloneDX) 생성, 베이스 이미지 버전 고정 (`latest` 금지) | SECURITY-10 |
| NFR-S11 | 데이터 변경 감사 | 업로드마다 `ingest_log` 추가 (삭제 · 수정 API 없음) | SECURITY-13 |
| NFR-S12 | 호환성 | `/api/v1`, 응답 필드 추가만 | NFR-07 |
| NFR-S13 | 테스트 | 라인 커버리지 80% 이상, PBT (hypothesis) 로 기간 · 급상승 · 연속 일수 · JSON 왕복 | NFR-06, PBT 부분 |

## Security Baseline 판정 (이 unit)

| 규칙 | 판정 | 근거 |
| --- | --- | --- |
| SECURITY-01 | compliant | NFR-S04. 저장 데이터 암호화는 서버 디스크 (볼륨) 암호화로, Environment Provisioning 에서 확인 항목 |
| SECURITY-02, 03 | compliant | NFR-S08, 프록시 접근 로그 (Caddy) |
| SECURITY-04 | compliant | NFR-S07 |
| SECURITY-05 | compliant | NFR-S06 |
| SECURITY-06 | compliant | 컨테이너 비 root 사용자, 읽기 전용 루트 파일시스템, 데이터 볼륨만 쓰기 |
| SECURITY-07 | compliant | 외부 포트 80 · 443 (프록시) 만, 앱은 내부 네트워크 |
| SECURITY-08 | compliant | 공개 = 읽기 전용 GET 만 (명시), 쓰기는 전부 토큰. 사용자별 객체 없음 (IDOR 해당 없음). 브라우저 클라이언트 없어 CORS 미허용 (기본 거부) |
| SECURITY-09 | compliant | NFR-S09, 기본 자격 증명 없음 |
| SECURITY-10 | compliant | NFR-S10 |
| SECURITY-11 | compliant | 인증은 `security.py` 로 분리, 속도 제한 · 검증 · 토큰 겹침 |
| SECURITY-12 | N/A (일부) | 사용자 계정 · 비밀번호 · 세션 없음. 하드코딩 비밀 금지는 compliant (환경 변수) |
| SECURITY-13 | compliant | NFR-S11, 안전한 역직렬화 (Pydantic 검사) |
| SECURITY-14 | compliant | NFR-S08 + Observability Setup 의 경보 (인증 실패 반복) |
| SECURITY-15 | compliant | NFR-S09, DB 연결은 컨텍스트 매니저로 해제 |
