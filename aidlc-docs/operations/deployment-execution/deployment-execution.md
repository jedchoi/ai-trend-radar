# Deployment Execution (runbook, 실행은 사용자)

## 0. 로컬 시험 배포 (같은 Wi-Fi, IP 접속)

| 단계 | 명령 | 확인 |
| --- | --- | --- |
| 서버 | `tool/local-server.sh --demo` | 출력된 `http://<PC IP>:8000/api/v1/health` 가 200 |
| 데이터 | `tool/local-pipeline.sh` | "완료: 논문 N편" |
| 앱 | `cd app && tool/bootstrap.sh && flutter run --profile`, 설정에 서버 주소 | 오늘 화면에 데모 표시 없이 표시 |

- 2026-11-17 클라우드 작업 공간에서 확인: IP 로 health · digests 200, `radar check` 통과, `.local/ingest-token` 으로 업로드 200
- 보안: http 는 같은 네트워크 시험용. Android release 빌드는 cleartext 차단 유지 (debug · profile 만 허용), 토큰은 `.local/` 권한 600

1. GitHub 비공개 저장소 생성 후 push → CI 통과 확인
2. Mac: `cd pipeline && uv run radar token` → 토큰은 키체인 (`security add-generic-password -U -s ai-trend-radar -a RADAR_INGEST_TOKEN -w '<토큰>'`), 해시는 메모
3. 서버: `git clone`, `deploy/server/.env` 작성, `docker compose up -d --build`, `curl https://<도메인>/api/v1/health`
4. Mac: `pipeline/deploy/install-mac.sh` → `~/.config/ai-trend-radar/config.toml` 의 `[server] url` 수정 → `uv run radar check` → `uv run radar daily --date <어제>` 로 첫 업로드
5. 앱: `cd app && tool/bootstrap.sh && flutter run --dart-define=RADAR_SERVER_URL=https://<도메인>` (또는 앱 설정에서 주소 입력)
6. 다음 날 08:00 이후 `tail ~/Library/Logs/ai-trend-radar.log` 와 앱에서 새 날짜 확인

이 세션에서 실행하지 않은 이유: 운영 환경 (서버 · Mac launchd) 은 명령만 제시한다는 Operations 안전 규칙, 서버 주소 · 도메인이 확인되지 않음.
