#!/bin/bash
# AI Trend Radar 한 번에 켜기 (FR-31). 여러 번 실행해도 안전하다.
#
#   1) Docker Desktop 에 PostgreSQL + API 서버를 띄운다 (데이터는 Docker 볼륨 radar-pg 에 남는다)
#   2) DB 가 비어 있으면 지난 90일 논문 · Hub 트렌드 · 뉴스를 채운다 (백그라운드, 로그 .local/logs/backfill.log)
#   3) 매일 06:00 자동 갱신을 등록한다 (macOS launchd)
#   4) 연결된 휴대폰이 있으면 서버 주소를 넣어 앱을 설치한다
#
# 사용:
#   tool/radar-up.sh                       전부
#   tool/radar-up.sh --database-url URL    이미 있는 Postgres 를 쓴다 (예: postgresql://postgres:pw@localhost:5432/radar)
#   tool/radar-up.sh --server-only         서버만 (채우기 · 일정 · 앱 설치 안 함)
#   tool/radar-up.sh --skip-app | --skip-schedule | --skip-backfill | --days 60 | --port 8000
#   tool/radar-up.sh --status | --logs | --stop | --backup | --psql
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL="$ROOT/.local"
COMPOSE_FILE="$ROOT/deploy/local/compose.yml"
ENV_FILE="$LOCAL/.env"
LABEL="com.jedchoi.ai-trend-radar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"

PORT=""
DB_URL=""
DAYS=90
DO_BACKFILL=1
DO_SCHEDULE=1
DO_APP=1
ACTION="up"
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --database-url) DB_URL="$2"; shift 2 ;;
    --days) DAYS="$2"; shift 2 ;;
    --skip-backfill) DO_BACKFILL=0; shift ;;
    --skip-schedule) DO_SCHEDULE=0; shift ;;
    --skip-app) DO_APP=0; shift ;;
    --server-only) DO_BACKFILL=0; DO_SCHEDULE=0; DO_APP=0; shift ;;
    --status|--logs|--stop|--backup|--psql) ACTION="${1#--}"; shift ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "알 수 없는 옵션: $1 (도움말: --help)"; exit 1 ;;
  esac
done

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
env_get() { [ -f "$ENV_FILE" ] && grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- || true; }

mkdir -p "$LOCAL/logs"
chmod 700 "$LOCAL"

# ---------- 준비: Docker ----------
need_docker() {
  command -v docker >/dev/null || { echo "docker 명령이 없습니다. Docker Desktop 을 설치 · 실행하세요."; exit 1; }
  if ! docker info >/dev/null 2>&1; then
    echo "Docker Desktop 을 시작합니다..."
    open -a Docker 2>/dev/null || true
    for _ in $(seq 1 90); do docker info >/dev/null 2>&1 && break; sleep 2; done
    docker info >/dev/null 2>&1 || { echo "Docker Desktop 이 응답하지 않습니다. 직접 실행한 뒤 다시 시도하세요."; exit 1; }
  fi
}

compose() {
  local profile=()
  [ "$(env_get RADAR_DB_MODE)" = "compose" ] && profile=(--profile db)
  # macOS 기본 bash 3.2 + set -u 에서 빈 배열을 안전하게 펼친다
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ${profile[@]+"${profile[@]}"} "$@"
}

# ---------- 보조 동작 ----------
case "$ACTION" in
  stop) need_docker; compose down; echo "서버를 멈췄습니다 (데이터는 볼륨에 남아 있음)"; exit 0 ;;
  logs) need_docker; compose logs -f --tail 200; exit 0 ;;
  psql)
    need_docker
    [ "$(env_get RADAR_DB_MODE)" = "compose" ] || { echo "외부 Postgres 를 쓰는 중입니다. 그 서버의 도구로 접속하세요."; exit 1; }
    exec docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile db exec db psql -U radar -d radar ;;
  backup)
    need_docker
    [ "$(env_get RADAR_DB_MODE)" = "compose" ] || { echo "외부 Postgres 는 그 서버에서 pg_dump 하세요."; exit 1; }
    mkdir -p "$LOCAL/backups"
    OUT="$LOCAL/backups/radar-$(date +%Y%m%d-%H%M).dump"
    compose exec -T db pg_dump -U radar -d radar -Fc > "$OUT"
    echo "백업: $OUT  (복원: docker compose ... exec -T db pg_restore -U radar -d radar --clean --if-exists < 파일)"
    exit 0 ;;
  status)
    P="$(env_get RADAR_PORT)"; P="${P:-8000}"
    curl -fsS "http://127.0.0.1:$P/api/v1/health" && echo || echo "서버 응답 없음 (tool/radar-up.sh --server-only 로 켜기)"
    launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state|last exit" || echo "06:00 일정: 등록 안 됨"
    tail -n 5 "$LOCAL/logs/daily.log" 2>/dev/null || true
    tail -n 3 "$LOCAL/logs/backfill.log" 2>/dev/null || true
    exit 0 ;;
esac

command -v uv >/dev/null || { echo "uv 가 필요합니다: brew install uv"; exit 1; }
command -v python3 >/dev/null || { echo "python3 가 필요합니다"; exit 1; }
need_docker

# ---------- 1) 비밀 · 설정 (.local/, 권한 600) ----------
say "1/5 설정 (.local/)"
TOKEN_FILE="$LOCAL/ingest-token"
if [ ! -s "$TOKEN_FILE" ]; then
  (umask 077; python3 -c "import secrets; print(secrets.token_urlsafe(32))" > "$TOKEN_FILE")
fi
chmod 600 "$TOKEN_FILE"
TOKEN_SHA256="$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1]).read().strip().encode()).hexdigest())" "$TOKEN_FILE")"
PG_PASSWORD="$(env_get POSTGRES_PASSWORD)"
[ -n "$PG_PASSWORD" ] || PG_PASSWORD="$(python3 -c "import secrets; print(secrets.token_hex(24))")"
PORT="${PORT:-$(env_get RADAR_PORT)}"; PORT="${PORT:-8000}"
DB_PORT="$(env_get RADAR_DB_PORT)"; DB_PORT="${DB_PORT:-5433}"
if [ -n "$DB_URL" ]; then
  MODE="external"
  # 컨테이너 안에서 PC 의 Postgres 에 닿도록 localhost → host.docker.internal
  CONTAINER_DB_URL="$(printf '%s' "$DB_URL" | sed -E 's#@(localhost|127\.0\.0\.1)([:/])#@host.docker.internal\2#')"
elif [ "$(env_get RADAR_DB_MODE)" = "external" ]; then
  MODE="external"; CONTAINER_DB_URL="$(env_get DATABASE_URL)"
else
  MODE="compose"; CONTAINER_DB_URL="postgresql://radar:$PG_PASSWORD@db:5432/radar"
fi
(umask 077; cat > "$ENV_FILE" <<ENV
# tool/radar-up.sh 가 만든 파일. 저장소에 올리지 않는다 (.gitignore: .local/)
RADAR_DB_MODE=$MODE
RADAR_PORT=$PORT
RADAR_DB_PORT=$DB_PORT
POSTGRES_PASSWORD=$PG_PASSWORD
DATABASE_URL=$CONTAINER_DB_URL
INGEST_TOKEN_SHA256=$TOKEN_SHA256
ENV
)
chmod 600 "$ENV_FILE"
if [ "$MODE" = "compose" ]; then
  OTHER_PG="$(docker ps --format '{{.Names}} ({{.Image}})' | grep -i postgres | grep -v '^ai-trend-radar' || true)"
  [ -n "$OTHER_PG" ] && echo "  참고: 실행 중인 다른 Postgres 가 있습니다: $OTHER_PG — 그 DB 를 쓰려면 --database-url 로 다시 실행"
  echo "  DB: Docker 의 postgres:16 (볼륨 radar-pg, PC 에서 접속: postgresql://radar:<.local/.env 의 비밀번호>@127.0.0.1:$DB_PORT/radar)"
else
  echo "  DB: 기존 Postgres (컨테이너에서 쓰는 주소는 .local/.env 의 DATABASE_URL)"
fi

# 파이프라인 설정: 이미 있으면 AI 설정은 그대로 두고 서버 주소만 맞춘다
CONFIG="$LOCAL/pipeline.toml"
if [ ! -f "$CONFIG" ]; then
  AI='provider = "none"'
  if CLAUDE_BIN="$(command -v claude 2>/dev/null)"; then
    AI="provider = \"cli\"
command = [\"$CLAUDE_BIN\", \"-p\"]
prompt_mode = \"arg\"
timeout_s = 300"
  elif GEMINI_BIN="$(command -v gemini 2>/dev/null)"; then
    AI="provider = \"cli\"
command = [\"$GEMINI_BIN\", \"-p\"]
prompt_mode = \"arg\"
timeout_s = 300"
  elif curl -fs http://localhost:11434/api/tags >/dev/null 2>&1; then
    MODEL="$(curl -fs http://localhost:11434/api/tags | python3 -c "import json,sys; m=json.load(sys.stdin).get('models',[]); print(m[0]['name'] if m else '')")"
    [ -n "$MODEL" ] && AI="provider = \"ollama\"
model = \"$MODEL\"
timeout_s = 300"
  fi
  cat > "$CONFIG" <<TOML
[server]
url = "http://127.0.0.1:$PORT"
token_env = "RADAR_INGEST_TOKEN"
token_file = "$TOKEN_FILE"

[ai]
$AI

[paths]
data_dir = "$LOCAL/pipeline-data"
TOML
fi
sed -i.bak "s#^url = \"http://127.0.0.1:[0-9]*\"#url = \"http://127.0.0.1:$PORT\"#" "$CONFIG" && rm -f "$CONFIG.bak"
echo "  분석 AI: $(grep -E '^(provider|command|model)' "$CONFIG" | tr '\n' ' ') (바꾸려면 .local/pipeline.toml 의 [ai])"

# ---------- 2) 서버 ----------
say "2/5 서버 (Docker: Postgres + API)"
compose up -d --build --wait
for _ in $(seq 1 30); do curl -fsS "http://127.0.0.1:$PORT/api/v1/health" >/dev/null 2>&1 && break; sleep 1; done
HEALTH="$(curl -fsS "http://127.0.0.1:$PORT/api/v1/health")" || { echo "API 가 응답하지 않습니다: tool/radar-up.sh --logs"; exit 1; }
echo "  $HEALTH"
(cd "$ROOT/pipeline" && uv sync --quiet)

# ---------- 3) 데이터 채우기 ----------
say "3/5 데이터"
if [ "$DO_BACKFILL" = 1 ] && printf '%s' "$HEALTH" | grep -q '"latest_date":null'; then
  echo "  DB 가 비어 있어 지난 ${DAYS}일을 채웁니다 (백그라운드)."
  echo "  - 1단계 (몇 분): 논문 · Hub 수집 → 바로 업로드 → 앱에서 보임"
  echo "  - 2단계 (오래 걸림): AI 분석으로 덮어쓰기, 뉴스 원문 · 분석, 주간 · 월간 리포트"
  nohup "$ROOT/tool/radar-daily.sh" --backfill "$DAYS" >> "$LOCAL/logs/backfill.log" 2>&1 &
  echo "  진행 상황: tail -f .local/logs/backfill.log"
elif [ "$DO_BACKFILL" = 1 ]; then
  echo "  이미 데이터가 있습니다 (마지막 날짜는 위 health). 빠진 날은 매일 실행이 채웁니다."
else
  echo "  건너뜀"
fi

# ---------- 4) 매일 06:00 ----------
say "4/5 매일 06:00 자동 갱신"
if [ "$DO_SCHEDULE" = 1 ] && [ "$(uname)" = "Darwin" ]; then
  mkdir -p "$HOME/Library/LaunchAgents"
  sed -e "s#__SCRIPT__#$ROOT/tool/radar-daily.sh#g" -e "s#__LOG__#$LOCAL/logs/launchd.log#g" \
    "$ROOT/deploy/local/schedule.plist" > "$PLIST"
  chmod +x "$ROOT/tool/radar-daily.sh"
  launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  echo "  등록: $PLIST (매일 06:00, 잠자기 중이었으면 깨어난 뒤 1회)"
  echo "  지금 한 번 실행: launchctl kickstart gui/$(id -u)/$LABEL"
else
  echo "  건너뜀"
fi

# ---------- 5) 앱 ----------
IP=""
if command -v ipconfig >/dev/null 2>&1; then
  for nic in en0 en1 en2 en3; do IP="$(ipconfig getifaddr "$nic" 2>/dev/null || true)"; [ -n "$IP" ] && break; done
fi
[ -z "$IP" ] && IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
SERVER_URL="http://${IP:-<이 PC 의 IP>}:$PORT"
say "5/5 앱 (서버 주소 $SERVER_URL 내장)"
if [ "$DO_APP" = 1 ] && [ -n "$IP" ] && command -v flutter >/dev/null; then
  DEVICE="$(flutter devices --machine 2>/dev/null | python3 -c "
import json, sys
try:
    devices = json.load(sys.stdin)
except ValueError:
    devices = []
phones = [d for d in devices if d.get('targetPlatform', '').startswith(('android', 'ios')) and not d.get('emulator')]
emulators = [d for d in devices if d.get('targetPlatform', '').startswith(('android', 'ios'))]
pick = (phones or emulators or [{}])[0]
print(pick.get('id', ''))
")"
  if [ -n "$DEVICE" ]; then
    (cd "$ROOT/app" && { [ -d android ] && grep -q usesCleartextTraffic android/app/src/profile/AndroidManifest.xml 2>/dev/null || tool/bootstrap.sh; } \
      && flutter run --profile --no-resident -d "$DEVICE" --dart-define=RADAR_SERVER_URL="$SERVER_URL") \
      && echo "  설치 완료 ($DEVICE). 앱을 열면 바로 데이터가 보입니다." \
      || echo "  설치 실패. 직접: tool/local-app.sh -d $DEVICE"
  else
    echo "  연결된 휴대폰이 없습니다. USB 연결 (Android: USB 디버깅 켜기) 후: tool/local-app.sh"
  fi
else
  echo "  건너뜀 (flutter 가 없거나 --skip-app). 나중에: tool/local-app.sh"
fi

cat <<MSG

완료
  휴대폰 앱 서버 주소: $SERVER_URL   (같은 Wi-Fi, 앱 설정에서 바꿀 수 있음)
  API 확인 (PC 브라우저): http://127.0.0.1:$PORT/api/v1/health   API 문서: /docs
  상태: tool/radar-up.sh --status    로그: tool/radar-up.sh --logs    멈춤: tool/radar-up.sh --stop
  * macOS 가 "들어오는 연결 허용" 을 물으면 허용하세요. Docker Desktop 은 로그인 시 자동 시작으로 두세요 (06:00 실행에 필요).
MSG
