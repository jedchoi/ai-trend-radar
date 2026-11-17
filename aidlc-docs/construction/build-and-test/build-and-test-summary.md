# Build and Test Summary (2026-11-17)

| 구분 | 결과 |
| --- | --- |
| backend-server 단위 | 71 passed, 커버리지 96% |
| pc-pipeline 단위 | 85 passed, 커버리지 94% (dry-run 설정 검사 수정 포함) |
| 통합 (파이프라인 → 서버 → 조회) | 2 passed |
| 계약 · 예시 응답 동기화 | 통과 |
| 성능 | p95 최대 50 ms (기준 300) |
| 보안 | 테스트 통과, pip-audit 취약점 없음 |
| mobile-app | 40 passed (사용자 Mac 에서 `tool/bootstrap.sh && flutter test`) |
| Docker 이미지 | ⚠️ 미실행 (Docker Hub 접근 불가). CI server-image job 에서 빌드 · 스모크 |
| 실제 Hugging Face 수집 | ⚠️ 미실행 (이 세션 셸에서 huggingface.co 차단). Mac 에서 `radar daily --dry-run` |

전체 명령: `tool/check.sh` (이 세션에서 `--skip-app` 으로 통과).
