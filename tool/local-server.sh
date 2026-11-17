#!/bin/bash
# 이 PC 에서 backend 서버를 띄우고 같은 Wi-Fi 의 휴대폰이 IP 로 접속하게 한다 (개발 · 시험용, http).
# 사용: tool/local-server.sh [--port 8000]
# 데이터 채우기: tool/local-backfill.sh (지난 90일 실제 데이터), 이후 매일 tool/local-pipeline.sh
# 운영 배포는 deploy/server (HTTPS) 를 쓴다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL="$ROOT/.local"
PORT=8000
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    *) echo "알 수 없는 옵션: $1"; exit 1 ;;
  esac
done
command -v uv >/dev/null || { echo "uv 가 필요합니다: brew install uv"; exit 1; }
mkdir -p "$LOCAL"
chmod 700 "$LOCAL"

# 1) 업로드 토큰 (이 PC 전용, 저장소 밖 .local/ 에 권한 600)
TOKEN_FILE="$LOCAL/ingest-token"
if [ ! -s "$TOKEN_FILE" ]; then
  (umask 077; python3 -c "import secrets; print(secrets.token_urlsafe(32))" > "$TOKEN_FILE")
fi
chmod 600 "$TOKEN_FILE"
TOKEN_SHA256="$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1]).read().strip().encode()).hexdigest())" "$TOKEN_FILE")"

# 2) 서버 가상환경
VENV="$LOCAL/server-venv"
if [ ! -x "$VENV/bin/uvicorn" ]; then
  uv venv -q --python ">=3.11" "$VENV"
  uv pip install -q --python "$VENV/bin/python" -r "$ROOT/server/requirements.txt"
fi

# 3) 파이프라인 설정 (같은 PC 에서 127.0.0.1 로 업로드). 이미 있으면 그대로 둔다 (AI 설정을 고쳤을 수 있음)
if [ ! -f "$LOCAL/pipeline.toml" ]; then
  # 쓸 수 있는 AI 를 찾는다: claude CLI → gemini CLI → Ollama → 없음 (Hugging Face 요약)
  AI='provider = "none"'
  if command -v claude >/dev/null 2>&1; then
    AI='provider = "cli"
command = ["claude", "-p"]
prompt_mode = "arg"
timeout_s = 300'
  elif command -v gemini >/dev/null 2>&1; then
    AI='provider = "cli"
command = ["gemini", "-p"]
prompt_mode = "arg"
timeout_s = 300'
  elif curl -fs http://localhost:11434/api/tags >/dev/null 2>&1; then
    MODEL="$(curl -fs http://localhost:11434/api/tags | python3 -c "import json,sys; m=json.load(sys.stdin).get('models',[]); print(m[0]['name'] if m else '')")"
    [ -n "$MODEL" ] && AI="provider = \"ollama\"
model = \"$MODEL\"
timeout_s = 300"
  fi
  cat > "$LOCAL/pipeline.toml" <<TOML
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
sed -i.bak "s#^url = \"http://127.0.0.1:[0-9]*\"#url = \"http://127.0.0.1:$PORT\"#" "$LOCAL/pipeline.toml" && rm -f "$LOCAL/pipeline.toml.bak"
AI_NOW="$(grep -E '^(provider|command|model)' "$LOCAL/pipeline.toml" | tr '\n' ' ')"
DB="$LOCAL/radar.db"

# 5) 휴대폰이 접속할 주소
IP=""
if command -v ipconfig >/dev/null 2>&1; then
  for nic in en0 en1 en2; do IP="$(ipconfig getifaddr "$nic" 2>/dev/null || true)"; [ -n "$IP" ] && break; done
fi
[ -z "$IP" ] && IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -z "$IP" ] && IP="<이 PC 의 IP>"

cat <<MSG

AI Trend Radar 로컬 서버
  휴대폰 앱 설정 > 서버 주소:  http://$IP:$PORT
  PC 브라우저 확인:            http://$IP:$PORT/api/v1/health   (API 문서: /docs)
  데이터: 지난 90일 채우기 = tool/local-backfill.sh, 매일 = tool/local-pipeline.sh  (다른 터미널)
  분석 AI: $AI_NOW  (바꾸려면 .local/pipeline.toml 의 [ai])
  앱 실행 (이 주소를 넣어 설치): tool/local-app.sh
  * 휴대폰과 PC 가 같은 Wi-Fi 여야 합니다. macOS 가 "들어오는 연결 허용" 을 물으면 허용하세요.
  * Android 는 debug · profile 빌드에서만 http 를 허용합니다:  cd app && flutter run --profile
  끝내려면 Ctrl+C
MSG

cd "$ROOT/server"
# 같은 PC 의 백필은 업로드가 몰리므로 업로드 한도를 넉넉히 (공개 조회 한도는 그대로)
export DB_PATH="$DB" INGEST_TOKEN_SHA256="$TOKEN_SHA256" ENABLE_DOCS=1 INGEST_RATE_PER_MIN=600
exec "$VENV/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$PORT" --no-server-header
