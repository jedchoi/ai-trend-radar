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
flutter pub get
echo "준비 완료: flutter run  (서버 주소 없이 실행하면 데모 데이터로 동작)"
