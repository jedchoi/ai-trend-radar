# Observability Setup

| 신호 | 위치 | 확인 방법 |
| --- | --- | --- |
| 서버 상태 · 최신 날짜 | `GET /api/v1/health` | `latest_date` 가 어제보다 오래되면 파이프라인 실패 |
| 접근 로그 (요청 id · 상태 · 소요 ms · IP) | api 컨테이너 stdout (JSON), Caddy 접근 로그 | `docker compose logs api` |
| 보안 이벤트 (`auth_failed`, `rate_limited`, `ingest_token_unconfigured`) | api stdout | `docker compose logs api \| grep security_event` |
| 업로드 감사 | SQLite `ingest_log` (추가 전용) | `sqlite3 radar.db 'select * from ingest_log order by seq desc limit 10'` |
| 파이프라인 실행 기록 | Mac `~/.local/share/ai-trend-radar/runs.jsonl` | `status`, `stage`, `ai_fallbacks` |
| 파이프라인 로그 | Mac `~/Library/Logs/ai-trend-radar.log` | `tail -f` |

## 경보 (SECURITY-14) — 최소 구성

- 서버 cron (매일 10:00): `curl -s https://<도메인>/api/v1/health` 의 `latest_date` 가 이틀 이상 지났거나, 지난 24시간 `auth_failed` 가 20회를 넘으면 메일 · 메신저 알림 (알림 수단은 사용자 환경에 맞춰 선택, 미확인이라 스크립트로 고정하지 않음)
- 로그 보존: Docker 로그 드라이버 기본 + 백업 디렉터리 30일. 90일 보존이 필요하면 `docker compose` 에 `logging.options.max-file` 조정

## 장애 대응 요점 (Incident Response SKIP 대신)

| 증상 | 조치 |
| --- | --- |
| 앱에 새 날짜가 안 보임 | Mac `runs.jsonl` 마지막 줄 `stage` 확인 → collect (HF 응답) · analyze (AI) · upload (토큰 · 서버) |
| upload 401 | 서버 `.env` 해시와 Mac 키체인 토큰 짝 확인 (`radar token` 으로 재발급) |
| AI 대체 (`ai_fallbacks`) 급증 | 제공자 키 · 한도 확인, 임시로 `provider = "none"` |
| 서버 다운 | `docker compose ps`, `docker compose up -d`, 필요하면 이전 커밋으로 재빌드 |
