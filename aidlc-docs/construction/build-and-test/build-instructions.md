# Build Instructions

| Unit | 명령 (저장소 루트 기준) | 산출물 |
| --- | --- | --- |
| backend-server | `docker build -t ai-trend-radar-api server` | 이미지 (해시 고정 의존성 `server/requirements.lock`) |
| pc-pipeline | `cd pipeline && uv sync --locked` | 가상환경 + `radar` 명령 |
| mobile-app | `cd app && tool/bootstrap.sh && flutter build apk --release --dart-define=RADAR_SERVER_URL=https://<도메인>` | APK |
