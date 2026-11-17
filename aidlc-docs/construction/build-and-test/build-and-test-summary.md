# Build and Test Summary (2026-11-17)

| 구분 | 결과 |
| --- | --- |
| backend-server 단위 | 72 passed, 커버리지 96% |
| pc-pipeline 단위 | 96 passed, 커버리지 94% (백필 · 429 대기 포함) |
| 통합 (파이프라인 → 서버 → 조회) | 3 passed (백필 포함) |
| 계약 · 예시 응답 동기화 | 통과 |
| 성능 | p95 최대 50 ms (기준 300) |
| 보안 | 테스트 통과, pip-audit 취약점 없음 |
| mobile-app | 40 passed (사용자 Mac, 데모 제거 전). 데모 제거 후 다시 실행 필요 |
| Docker 이미지 | ⚠️ 미실행 (Docker Hub 접근 불가). CI server-image job 에서 빌드 · 스모크 |
| 실제 Hugging Face 수집 | ⚠️ 미실행 (이 세션 셸에서 huggingface.co 차단). Mac 에서 `radar daily --dry-run` |

전체 명령: `tool/check.sh` (이 세션에서 `--skip-app` 으로 통과).

## 2주기 (2026-11-17, PostgreSQL · 뉴스 · 원문 · 06:00 일정 · 앱 개선)

| 구분 | 결과 |
| --- | --- |
| backend-server 단위 (실제 PostgreSQL 16) | 88 passed, 커버리지 96% (뉴스 8 · 원문 3 · 저장소 5 추가) |
| pc-pipeline 단위 | 115 passed, 커버리지 93% (뉴스 14 · 원문 5 추가) |
| 통합 (파이프라인 → 실제 HTTP 서버 → PostgreSQL) | 4 passed (뉴스 · 원문 · 원본 JSON 추가) |
| 계약 · 예시 응답 동기화 | 통과 (news_list · news_detail 추가). SQLite → Postgres 전환 직후 기존 8개 예시가 바이트 단위로 같음 |
| 성능 (1만 건, Postgres) | p95 최대 126 ms (검색), 기준 300 ms |
| 보안 | pip-audit 취약점 없음 (psycopg 3.3.9 포함). 업로드 한도 10 MB, 원본 JSON 은 응답에 노출 안 함 (테스트) |
| 한 명령 실행 리허설 | `tool/radar-up.sh --days 14` 를 가짜 docker (실제 API + 실제 Postgres) · 가짜 Hugging Face (논문 · 블로그 · 본문) · 가짜 claude CLI 로 실행: 백필 14일 (논문 130편, 원본 JSON 130, 본문 원문 50), 뉴스 8건 (원문 · AI 요약), 주간 3 · 월간 1 리포트, 다시 실행 시 "이미 데이터 있음", `tool/radar-daily.sh` 멱등 (새 글 0건) |
| shellcheck | `tool/radar-up.sh`, `tool/radar-daily.sh` 경고 없음 |
| mobile-app | ⚠️ 미실행: 이 환경에서 Flutter · Dart 를 받을 수 없음 (pub.dev · storage.googleapis.com 차단). 테스트 54개 (2주기 14개 추가) 를 작성했고 사용자 Mac 에서 `cd app && flutter test` 필요 |
| Docker Desktop 실행 · 06:00 launchd · 휴대폰 설치 | ⚠️ 미실행: 이 세션 셸은 Mac 의 Docker · USB · launchd 에 접근 불가. 사용자 Mac 에서 `tool/radar-up.sh` 한 번 |
| 실제 Hugging Face 수집 | ⚠️ 미실행 (이 환경에서 차단). RSS 형식은 2026-11-17 실제 피드로 확인 (title · pubDate · link · guid, 본문 없음) |
