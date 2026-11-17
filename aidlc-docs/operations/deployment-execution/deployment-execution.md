# Deployment Execution (runbook, 실행은 사용자)

1. GitHub 비공개 저장소 생성 후 push → CI 통과 확인
2. Mac: `cd pipeline && uv run radar token` → 토큰은 키체인 (`security add-generic-password -U -s ai-trend-radar -a RADAR_INGEST_TOKEN -w '<토큰>'`), 해시는 메모
3. 서버: `git clone`, `deploy/server/.env` 작성, `docker compose up -d --build`, `curl https://<도메인>/api/v1/health`
4. Mac: `pipeline/deploy/install-mac.sh` → `~/.config/ai-trend-radar/config.toml` 의 `[server] url` 수정 → `uv run radar check` → `uv run radar daily --date <어제>` 로 첫 업로드
5. 앱: `cd app && tool/bootstrap.sh && flutter run --dart-define=RADAR_SERVER_URL=https://<도메인>` (또는 앱 설정에서 주소 입력)
6. 다음 날 08:00 이후 `tail ~/Library/Logs/ai-trend-radar.log` 와 앱에서 새 날짜 확인

이 세션에서 실행하지 않은 이유: 운영 환경 (서버 · Mac launchd) 은 명령만 제시한다는 Operations 안전 규칙, 서버 주소 · 도메인이 확인되지 않음.
