#!/bin/bash
# 로컬 서버 (tool/radar-up.sh) 로 파이프라인을 돌린다. 인자는 `radar daily` 에 그대로 넘긴다.
# 예: tool/local-pipeline.sh                 (어제 + 빠진 날)
#     tool/local-pipeline.sh --date 2026-11-16
# AI 를 쓰려면 .local/pipeline.toml 의 [ai] 를 바꾼다 (pipeline/deploy/config.example.toml 참고).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$ROOT/.local/pipeline.toml"
[ -f "$CONFIG" ] || { echo "먼저 tool/radar-up.sh 를 실행하세요"; exit 1; }
cd "$ROOT/pipeline"
exec uv run --quiet radar --config "$CONFIG" daily "$@"
