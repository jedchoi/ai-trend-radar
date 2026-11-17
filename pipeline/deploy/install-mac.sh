#!/bin/bash
# PC 파이프라인 설치 (macOS). 여러 번 실행해도 안전하다.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
CONFIG_DIR="$HOME/.config/ai-trend-radar"
PLIST="$HOME/Library/LaunchAgents/com.jedchoi.ai-trend-radar.plist"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv 가 없습니다. 먼저 설치하세요: brew install uv  (또는 https://docs.astral.sh/uv/ 의 설치 방법)"
  exit 1
fi

echo "1/4 의존성 설치 (uv sync)"
(cd "$REPO_DIR/pipeline" && uv sync --quiet)

echo "2/4 설정 파일"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.toml" ]; then
  cp "$REPO_DIR/pipeline/deploy/config.example.toml" "$CONFIG_DIR/config.toml"
  echo "  $CONFIG_DIR/config.toml 을 만들었습니다. [server] url 을 서버 주소로 고치세요."
else
  echo "  기존 설정 유지: $CONFIG_DIR/config.toml"
fi

echo "3/4 예약 실행 등록 (매일 08:00)"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
sed -e "s#__REPO_DIR__#$REPO_DIR#g" -e "s#__HOME__#$HOME#g" \
  "$REPO_DIR/pipeline/deploy/com.jedchoi.ai-trend-radar.plist" > "$PLIST"
chmod +x "$REPO_DIR/pipeline/deploy/run-daily.sh"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "4/4 남은 일 (직접 실행):"
cat <<MSG
  - 토큰 만들기:            (cd "$REPO_DIR/pipeline" && uv run radar token)
  - 토큰을 키체인에 저장:    security add-generic-password -U -s ai-trend-radar -a RADAR_INGEST_TOKEN -w '<토큰>'
  - (AI API 를 쓸 때) 키 저장: security add-generic-password -U -s ai-trend-radar -a ANTHROPIC_API_KEY -w '<키>'
  - 확인:                   RADAR_INGEST_TOKEN='<토큰>' uv run --project "$REPO_DIR/pipeline" radar check
  - 지금 한 번 실행:         launchctl kickstart "gui/$(id -u)/com.jedchoi.ai-trend-radar"
  - 로그:                   tail -f ~/Library/Logs/ai-trend-radar.log
MSG
