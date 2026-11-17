#!/bin/bash
# launchd 가 매일 부르는 실행 스크립트. 비밀은 macOS 키체인에서 읽어 이 프로세스에만 넘긴다.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
CONFIG="${RADAR_CONFIG:-$HOME/.config/ai-trend-radar/config.toml}"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

keychain() {  # $1 = 계정 이름 (환경 변수 이름과 같게 저장)
  security find-generic-password -s ai-trend-radar -a "$1" -w 2>/dev/null || true
}

# 업로드 토큰과 (있으면) AI 키를 키체인에서 읽는다
RADAR_INGEST_TOKEN="$(keychain RADAR_INGEST_TOKEN)"
export RADAR_INGEST_TOKEN
for name in ANTHROPIC_API_KEY OPENAI_API_KEY GEMINI_API_KEY; do
  value="$(keychain "$name")"
  if [ -n "$value" ]; then export "$name=$value"; fi
done

echo "=== $(date '+%Y-%m-%d %H:%M:%S') radar daily ==="
cd "$REPO_DIR/pipeline"
exec uv run --quiet radar --config "$CONFIG" daily "$@"
