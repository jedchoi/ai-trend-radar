# AI 트렌드 레이더 — 모바일 앱 (Flutter)

```sh
tool/bootstrap.sh          # 처음 한 번: android · ios 폴더 생성, 인터넷 권한, pub get
flutter test               # 단위 · 위젯 테스트
flutter run                # 서버 주소가 없으면 데모 데이터로 실행
flutter run --dart-define=RADAR_SERVER_URL=https://radar.example.com
flutter build apk --release --dart-define=RADAR_SERVER_URL=https://radar.example.com
```

- 데모 데이터는 `assets/demo/` (서버의 `contract/samples/` 복사본). 서버 계약이 바뀌면 `server/tools/make_samples.py` 를 다시 돌리고 복사한다 (CI 가 두 폴더가 같은지 검사)
- 설정 화면에서 서버 주소 · 관심 키워드 · "AI 에게 묻기" 대상을 바꿀 수 있다
