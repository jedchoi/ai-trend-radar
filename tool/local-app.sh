#!/bin/bash
# 로컬 서버 주소 (http://<이 PC IP>:<포트>) 를 넣어 앱을 휴대폰에 설치 · 실행한다 (profile 빌드: http 허용, release 에 가까운 속도).
# 사용: tool/local-app.sh [--port 8000] [flutter run 의 다른 인자, 예: -d <기기 ID>]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT=8000
if [ "${1:-}" = "--port" ]; then PORT="$2"; shift 2; fi
IP=""
if command -v ipconfig >/dev/null 2>&1; then
  for nic in en0 en1 en2; do IP="$(ipconfig getifaddr "$nic" 2>/dev/null || true)"; [ -n "$IP" ] && break; done
fi
[ -z "$IP" ] && IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -n "$IP" ] || { echo "이 PC 의 IP 를 찾지 못했습니다"; exit 1; }
cd "$ROOT/app"
if ! grep -q usesCleartextTraffic android/app/src/profile/AndroidManifest.xml 2>/dev/null; then
  tool/bootstrap.sh
fi
echo "서버 주소: http://$IP:$PORT  (앱 설정에서 언제든 바꿀 수 있음)"
exec flutter run --profile --dart-define=RADAR_SERVER_URL="http://$IP:$PORT" "$@"
