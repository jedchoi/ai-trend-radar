# AI 트렌드 레이더 — 모바일 앱 (Flutter)

```sh
tool/bootstrap.sh          # 처음 한 번: android · ios 폴더 생성, 인터넷 권한, pub get
flutter test               # 단위 · 위젯 테스트
../tool/local-app.sh       # 이 PC 의 로컬 서버 주소를 넣어 profile 빌드로 실행
flutter run --dart-define=RADAR_SERVER_URL=https://radar.example.com
flutter build apk --release --dart-define=RADAR_SERVER_URL=https://radar.example.com
```

- 서버 주소가 없으면 설정 안내를 보여 준다 (데모 데이터 없음). 테스트는 `../contract/samples/` 의 실제 응답 형식을 쓴다
- 설정 화면에서 서버 주소 · 관심 키워드 · "AI 에게 묻기" 대상을 바꿀 수 있다
