#!/bin/bash
# 로컬 서버에 지난 N 일 (기본 90일) 의 실제 Hugging Face 데이터를 채운다.
#   1단계: 수집 → AI 없이 바로 업로드 (몇 분이면 앱에서 볼 수 있음)
#   2단계: .local/pipeline.toml 의 AI 로 최근 날부터 다시 분석해 덮어쓰기 (오래 걸림, 중단해도 다시 실행하면 이어서)
#   3단계: 주간 · 월간 리포트
# 사용: tool/local-backfill.sh [--days 90] [--until YYYY-MM-DD] [--no-reports]
# 먼저 다른 터미널에서 tool/local-server.sh 를 실행해 둔다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$ROOT/.local/pipeline.toml"
[ -f "$CONFIG" ] || { echo "먼저 tool/local-server.sh 를 실행하세요"; exit 1; }
cd "$ROOT/pipeline"
exec uv run --quiet radar --config "$CONFIG" backfill "$@"
