#!/bin/bash
# android · ios 플랫폼 폴더를 만들고 (lib/ · test/ 는 그대로 둔다) 인터넷 권한을 넣는다. 여러 번 실행해도 안전하다.
set -euo pipefail
cd "$(dirname "$0")/.."
flutter create . --project-name ai_trend_radar --org com.jedchoi --platforms android,ios >/dev/null
MANIFEST=android/app/src/main/AndroidManifest.xml
if ! grep -q "android.permission.INTERNET" "$MANIFEST"; then
  # release 빌드는 기본 manifest 에 인터넷 권한이 없다
  perl -0pi -e 's#(<manifest[^>]*>)#$1\n    <uses-permission android:name="android.permission.INTERNET"/>#' "$MANIFEST"
fi
sed -i.bak 's#android:label="ai_trend_radar"#android:label="AI 트렌드 레이더"#' "$MANIFEST" && rm -f "$MANIFEST.bak"

# 로컬 서버 (http://<PC IP>:8000) 접속: debug · profile 빌드에서만 http 허용. release 는 https 만 (SECURITY-01)
for variant in debug profile; do
  M=android/app/src/$variant/AndroidManifest.xml
  if [ -f "$M" ] && ! grep -q "usesCleartextTraffic" "$M"; then
    perl -0pi -e 's#</manifest>#    <application android:usesCleartextTraffic="true" />\n</manifest>#' "$M"
  fi
done
# iOS: 같은 네트워크의 http 서버 허용 (ATS 로컬 네트워크 예외) + 로컬 네트워크 사용 설명
PLIST=ios/Runner/Info.plist
if [ -f "$PLIST" ] && [ -x /usr/libexec/PlistBuddy ]; then
  if ! /usr/libexec/PlistBuddy -c "Print :NSAppTransportSecurity:NSAllowsLocalNetworking" "$PLIST" >/dev/null 2>&1; then
    /usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity dict" "$PLIST" 2>/dev/null || true
    /usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity:NSAllowsLocalNetworking bool true" "$PLIST"
    /usr/libexec/PlistBuddy -c "Add :NSAppTransportSecurity:NSExceptionDomains dict" "$PLIST" 2>/dev/null || true
  fi
  /usr/libexec/PlistBuddy -c "Print :NSLocalNetworkUsageDescription" "$PLIST" >/dev/null 2>&1 || \
    /usr/libexec/PlistBuddy -c "Add :NSLocalNetworkUsageDescription string '같은 네트워크의 AI 트렌드 레이더 서버에 접속합니다'" "$PLIST"
fi

flutter pub get
echo "준비 완료: flutter run  (서버 주소 없이 실행하면 데모 데이터로 동작)"
echo "로컬 서버 (http) 에 붙일 때는 debug 또는 profile 빌드: flutter run --profile"
