# Unit of Work

진행 순서: backend-server → pc-pipeline → mobile-app

| 순서 | Unit | 디렉터리 | 언어 · 런타임 | 범위 | 배포 위치 |
| --- | --- | --- | --- | --- | --- |
| 1 | `backend-server` | `server/`, `contract/` | Python 3.12, FastAPI, PostgreSQL 16 | C-S1 ~ C-S7, API 계약 · 예시 응답 | 사용자의 Linux 서버 (Docker) |
| 2 | `pc-pipeline` | `pipeline/` | Python 3.11+, httpx, Pydantic | C-P1 ~ C-P10, 프롬프트, launchd 설정 | 사용자 Mac |
| 3 | `mobile-app` | `app/` | Flutter 3.41.7 (CI 고정), Dart | C-A1 ~ C-A10 | Android (APK), iOS 는 같은 코드 |

## 저장소 구조

```text
ai-trend-radar/
├── server/            # unit 1
├── contract/samples/  # unit 1 이 만드는 예시 응답 (앱 테스트 입력)
├── pipeline/          # unit 2
├── app/               # unit 3
├── deploy/            # Operations
├── .github/workflows/ # Operations
├── tool/check.sh      # 전체 점검
└── aidlc-docs/        # 문서 전용
```
