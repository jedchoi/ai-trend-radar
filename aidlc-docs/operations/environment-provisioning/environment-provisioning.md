# Environment Provisioning

| 환경 | 준비 | 파일 | 상태 |
| --- | --- | --- | --- |
| 서버 (사용자 Linux 서버, Docker 확인됨) | 도메인 A 레코드, 80 · 443 개방, `.env` (도메인 · 토큰 해시) | `deploy/server/` | 명령 제시만 (운영 환경은 사용자가 실행) |
| 사용자 Mac | uv 설치, `install-mac.sh` (설정 · launchd 등록), 키체인에 토큰 · 키 | `pipeline/deploy/` | 명령 제시만 |
| 휴대폰 | APK 설치 또는 `flutter run` | `app/` | - |

확인 항목: 서버 디스크 · 볼륨 암호화 여부 (SECURITY-01 저장 데이터), 백업 cron 등록 (`deploy/server/backup.sh`).
