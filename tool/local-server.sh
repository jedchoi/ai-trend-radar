#!/bin/bash
# 이 PC 에서 backend 서버를 띄우고 같은 Wi-Fi 의 휴대폰이 IP 로 접속하게 한다 (개발 · 시험용, http).
# 사용: tool/local-server.sh [--port 8000] [--demo]
#   --demo  DB 가 비어 있으면 예시 데이터 (contract/samples 와 같은 내용) 를 넣는다
# 운영 배포는 deploy/server (HTTPS) 를 쓴다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL="$ROOT/.local"
PORT=8000
DEMO=0
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --demo) DEMO=1; shift ;;
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
  uv pip install -q --python "$VENV/bin/python" -r "$ROOT/server/requirements.txt" httpx==0.28.1
fi

# 3) 파이프라인 설정 (같은 PC 에서 127.0.0.1 로 업로드)
cat > "$LOCAL/pipeline.toml" <<TOML
[server]
url = "http://127.0.0.1:$PORT"
token_env = "RADAR_INGEST_TOKEN"
token_file = "$TOKEN_FILE"

[ai]
provider = "none"

[paths]
data_dir = "$LOCAL/pipeline-data"
TOML

# 4) 예시 데이터
DB="$LOCAL/radar.db"
if [ "$DEMO" = 1 ] && [ ! -s "$DB" ]; then
  (cd "$ROOT/server" && "$VENV/bin/python" -m tools.make_samples --db "$DB" --out "$LOCAL/samples" >/dev/null)
  echo "예시 데이터를 넣었습니다 ($DB)"
fi

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
  오늘 데이터 올리기 (다른 터미널): tool/local-pipeline.sh
  * 휴대폰과 PC 가 같은 Wi-Fi 여야 합니다. macOS 가 "들어오는 연결 허용" 을 물으면 허용하세요.
  * Android 는 debug · profile 빌드에서만 http 를 허용합니다:  cd app && flutter run --profile
  끝내려면 Ctrl+C
MSG

cd "$ROOT/server"
export DB_PATH="$DB" INGEST_TOKEN_SHA256="$TOKEN_SHA256" ENABLE_DOCS=1
exec "$VENV/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$PORT" --no-server-header
