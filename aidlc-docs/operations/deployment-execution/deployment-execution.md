# Deployment Execution (runbook, 실행은 사용자)

## 0. 로컬 실데이터 배포 (같은 Wi-Fi, IP 접속)

| 단계 | 명령 | 확인 |
| --- | --- | --- |
| 서버 | `tool/radar-up.sh` (2주기: Docker Desktop 의 Postgres + API, 백필 · 06:00 일정 · 앱 설치까지) | 출력된 `http://<PC IP>:8000/api/v1/health` 가 200, 분석 AI 표시 |
| 90일 데이터 | `tool/local-backfill.sh` | 1단계 "[n/90] 올림" → 2단계 "[AI n/m] 분석" → "리포트 … 올림" |
| 앱 | `tool/local-app.sh -d <기기 ID>` | 오늘 화면에 실제 논문 |
| 매일 | `tool/local-pipeline.sh` (또는 launchd) | 어제 날짜 추가 |

- 2026-11-17 클라우드 작업 공간에서 확인 (Hugging Face 는 가짜 응답 서버, AI 는 가짜 `claude` CLI): 90일 1단계 업로드 · 2단계 AI 90일 · 리포트 주 12 + 월 4, 전체 61초. 업로드 429 문제를 이 시험에서 발견해 수정 (BR-P23, NFR-S05)
- 보안: http 는 같은 네트워크 시험용. Android release 빌드는 cleartext 차단 유지, 토큰은 `.local/` 권한 600

## 운영 배포

1. GitHub 비공개 저장소 생성 후 push → CI 통과 확인
2. Mac: `cd pipeline && uv run radar token` → 토큰은 키체인 (`security add-generic-password -U -s ai-trend-radar -a RADAR_INGEST_TOKEN -w '<토큰>'`), 해시는 메모
3. 서버: `git clone`, `deploy/server/.env` 작성, `docker compose up -d --build`, `curl https://<도메인>/api/v1/health`
4. Mac: `pipeline/deploy/install-mac.sh` → `~/.config/ai-trend-radar/config.toml` 의 `[server] url` 수정 → `uv run radar check` → `uv run radar daily --date <어제>` 로 첫 업로드
5. 앱: `cd app && tool/bootstrap.sh && flutter run --dart-define=RADAR_SERVER_URL=https://<도메인>` (또는 앱 설정에서 주소 입력)
6. 다음 날 06:00 이후 `tool/radar-up.sh --status` (또는 `.local/logs/daily.log`) 와 앱에서 새 날짜 · 뉴스 확인

이 세션에서 실행하지 않은 이유: 운영 환경 (서버 · Mac launchd) 은 명령만 제시한다는 Operations 안전 규칙, 서버 주소 · 도메인이 확인되지 않음.

## 릴리즈 APK (2026-11-18)

| 할 일 | 명령 | 확인 |
| --- | --- | --- |
| 로컬 서버용 릴리즈 APK | `tool/build-apk.sh` | `dist/ai-trend-radar-1.0.0-<날짜>.apk` 생성, 출력의 서버 주소가 `http://<PC IP>:8000` |
| 공개 서버용 | `tool/build-apk.sh --server-url https://<도메인>` | http 허용 파일을 만들지 않음 (release 기본 https) |
| 설치 | `tool/build-apk.sh --install` 또는 APK 파일을 휴대폰에서 열기 | 앱 첫 화면에 데이터 |

결정: 로컬 서버가 http 이므로 http 주소로 빌드할 때만 cleartext 를 허용한다 (개인용 빌드, SECURITY-01 예외를 빌드 단위로 한정). 서명은 Flutter 기본 debug 키 — 스토어 배포 시 별도 키 필요.
