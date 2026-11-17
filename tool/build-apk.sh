#!/bin/bash
# 릴리즈 APK 만들기 (서버 주소 내장 → 설치하면 바로 동작, FR-29).
#   tool/build-apk.sh                         이 PC 의 로컬 서버 (http://<PC IP>:<포트>) 주소를 넣어 빌드
#   tool/build-apk.sh --server-url https://radar.example.com   공개 서버 (https) 주소로 빌드
#   tool/build-apk.sh --install               빌드 후 USB 로 연결된 Android 기기에 설치 (adb)
# 결과: dist/ai-trend-radar-<버전>-<날짜>.apk
#
# http 주소로 빌드하면 이 빌드에만 http 접속을 허용한다 (release 기본은 https 만, SECURITY-01).
# 같은 Wi-Fi 의 내 서버용 개인 빌드라는 뜻이다. 서명은 Flutter 기본 (debug 키) 이라 직접 설치용이고,
# Play 스토어에 올리려면 별도 서명 키가 필요하다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/app"
URL=""
INSTALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --server-url) URL="$2"; shift 2 ;;
    --install) INSTALL=1; shift ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "알 수 없는 옵션: $1 (도움말: --help)"; exit 1 ;;
  esac
done
command -v flutter >/dev/null || { echo "flutter 가 필요합니다 (3.41.7)"; exit 1; }

if [ -z "$URL" ]; then
  PORT="$(grep -E '^RADAR_PORT=' "$ROOT/.local/.env" 2>/dev/null | cut -d= -f2 || true)"; PORT="${PORT:-8000}"
  IP=""
  if command -v ipconfig >/dev/null 2>&1; then
    for nic in en0 en1 en2 en3; do IP="$(ipconfig getifaddr "$nic" 2>/dev/null || true)"; [ -n "$IP" ] && break; done
  fi
  [ -z "$IP" ] && IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  [ -n "$IP" ] || { echo "이 PC 의 IP 를 찾지 못했습니다. --server-url 로 주소를 주세요"; exit 1; }
  URL="http://$IP:$PORT"
fi
case "$URL" in
  http://*|https://*) ;;
  *) echo "서버 주소는 http:// 또는 https:// 로 시작해야 합니다: $URL"; exit 1 ;;
esac

cd "$APP"
tool/bootstrap.sh >/dev/null   # android 폴더 · 인터넷 권한 (여러 번 실행해도 안전)

OVERLAY="android/app/src/release/AndroidManifest.xml"
cleanup() { [ -n "${CREATED_OVERLAY:-}" ] && rm -f "$OVERLAY" && rmdir android/app/src/release 2>/dev/null || true; }
trap cleanup EXIT
if [ "${URL#http://}" != "$URL" ] && [ ! -f "$OVERLAY" ]; then
  mkdir -p "$(dirname "$OVERLAY")"
  cat > "$OVERLAY" <<'XML'
<!-- tool/build-apk.sh 가 http 서버 주소로 빌드할 때만 잠깐 만드는 파일 (빌드 후 지움) -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:usesCleartextTraffic="true" />
</manifest>
XML
  CREATED_OVERLAY=1
  echo "http 서버 주소 → 이 빌드에만 http 접속 허용"
fi

echo "서버 주소: $URL"
flutter build apk --release --dart-define=RADAR_SERVER_URL="$URL"

VERSION="$(grep -E '^version:' pubspec.yaml | awk '{print $2}' | cut -d+ -f1)"
mkdir -p "$ROOT/dist"
OUT="$ROOT/dist/ai-trend-radar-$VERSION-$(date +%Y%m%d).apk"
cp build/app/outputs/flutter-apk/app-release.apk "$OUT"
SIZE="$(du -h "$OUT" | cut -f1)"
SHA="$( (shasum -a 256 "$OUT" 2>/dev/null || sha256sum "$OUT") | cut -d' ' -f1)"

if [ "$INSTALL" = 1 ]; then
  ADB="$(command -v adb || echo "$HOME/Library/Android/sdk/platform-tools/adb")"
  if [ -x "$ADB" ] && [ -n "$("$ADB" devices | awk 'NR>1 && $2=="device"')" ]; then
    "$ADB" install -r "$OUT" && echo "기기에 설치했습니다"
  else
    echo "연결된 Android 기기가 없습니다 (USB 디버깅 확인). APK 파일을 휴대폰으로 옮겨 설치해도 됩니다."
  fi
fi

cat <<MSG

완료: $OUT  ($SIZE)
  SHA-256: $SHA
  서버 주소: $URL  (앱 설정에서 바꿀 수 있음)
  설치: USB 연결 후 tool/build-apk.sh --install, 또는 APK 를 휴대폰으로 옮겨 열기 ("알 수 없는 앱 설치" 허용 필요)
MSG
