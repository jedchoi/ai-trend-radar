# Infrastructure Design — pc-pipeline

## 확인된 환경 (ID-1)

- 사용자 Mac (Apple Silicon, `/Volumes/Mac990/Project` 에 프로젝트) — 이 세션에서 확인
- 그 밖의 도구 (uv, AI CLI 설치 여부) 는 확인되지 않음 → 설치 스크립트가 확인하고 안내

## 구성

| 항목 | 내용 |
| --- | --- |
| 실행 | `launchd` 사용자 에이전트 `com.jedchoi.ai-trend-radar` 가 매일 08:00 (Mac 시간대 = KST) 에 `pipeline/deploy/run-daily.sh` 실행. 잠자기 중 놓친 실행은 깨어날 때 1회 실행 (launchd 동작), 꺼져 있던 날은 BR-P14 로 채움 |
| 비밀 | macOS 키체인 (`security add-generic-password -s ai-trend-radar -a ingest-token`, AI 키는 `-a <ENV 이름>`) → `run-daily.sh` 가 읽어 환경 변수로 넘김. plist · 설정 파일에는 비밀 없음 |
| 설정 | `~/.config/ai-trend-radar/config.toml` |
| 데이터 | `~/.local/share/ai-trend-radar/` (state.json, runs.jsonl, raw/) |
| 로그 | `~/Library/Logs/ai-trend-radar.log` (launchd 표준 출력) |
| 설치 | `pipeline/deploy/install-mac.sh` (uv 확인, 설정 복사, plist 설치 · 등록). 키체인 등록 명령은 안내만 |
