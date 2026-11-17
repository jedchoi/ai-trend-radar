#!/bin/bash
# 매일 06:00 launchd 가 부르는 실행 (FR-28, BR-P35). 직접 실행해도 된다.
#   tool/radar-daily.sh                  어제 + 빠진 날 논문 · Hub → 뉴스 → (월요일 · 1일) 리포트
#   tool/radar-daily.sh --backfill 90    지난 90일 채우기 (tool/radar-up.sh 가 처음 한 번 부른다)
# 같은 PC 에서 동시에 두 개가 돌지 않도록 잠근다 (.local/run.lock). 서버가 꺼져 있으면 켠다.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL="$ROOT/.local"
CONFIG="$LOCAL/pipeline.toml"
LOCK="$LOCAL/run.lock"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PYTHONUNBUFFERED=1  # 로그 파일에 진행 상황이 바로 보이도록
mkdir -p "$LOCAL/logs"
[ -f "$CONFIG" ] || { echo "먼저 tool/radar-up.sh 를 실행하세요"; exit 3; }

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# 잠금: 앞선 실행 (예: 오래 걸리는 백필) 이 끝날 때까지 최대 8시간 기다린다. 죽은 프로세스의 잠금은 치운다
for _ in $(seq 1 2880); do
  if mkdir "$LOCK" 2>/dev/null; then echo $$ > "$LOCK/pid"; break; fi
  OWNER="$(cat "$LOCK/pid" 2>/dev/null || true)"
  if [ -n "$OWNER" ] && ! kill -0 "$OWNER" 2>/dev/null; then rm -rf "$LOCK"; continue; fi
  sleep 10
done
[ -d "$LOCK" ] && [ "$(cat "$LOCK/pid" 2>/dev/null)" = "$$" ] || { log "잠금을 얻지 못함"; exit 1; }
trap 'rm -rf "$LOCK"' EXIT

PORT="$(grep -E '^RADAR_PORT=' "$LOCAL/.env" 2>/dev/null | cut -d= -f2)"; PORT="${PORT:-8000}"
if ! curl -fsS "http://127.0.0.1:$PORT/api/v1/health" >/dev/null 2>&1; then
  log "서버 응답 없음 → Docker 서버 켜기"
  "$ROOT/tool/radar-up.sh" --server-only >/dev/null 2>&1 || true
  for _ in $(seq 1 60); do curl -fsS "http://127.0.0.1:$PORT/api/v1/health" >/dev/null 2>&1 && break; sleep 3; done
fi

cd "$ROOT/pipeline" || exit 1
if [ "${1:-}" = "--backfill" ]; then
  log "백필 시작 (${2:-90}일)"
  uv run --quiet radar --config "$CONFIG" backfill --days "${2:-90}"
  CODE=$?
else
  log "매일 실행 시작"
  uv run --quiet radar --config "$CONFIG" daily 2>&1 | tee -a "$LOCAL/logs/daily.log"
  CODE=${PIPESTATUS[0]}
fi
log "끝 (종료 코드 $CODE)"
exit "$CODE"
