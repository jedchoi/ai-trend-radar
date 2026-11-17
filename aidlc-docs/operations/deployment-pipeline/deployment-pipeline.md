# Deployment Pipeline

- 대상 (확인됨): GitHub 저장소 (사용자 계정 jedchoi, 비공개 저장소 사용 패턴) + Actions. 저장소는 아직 만들지 않음 → 사용자가 `git remote add origin ... && git push`
- 파일: `.github/workflows/ci.yml`

| job | 하는 일 | 실패 시 |
| --- | --- | --- |
| server | ruff, pytest (커버리지 80%), 성능, pip-audit, SBOM, 예시 응답 동기화 | 병합 금지 |
| server-image | Docker 빌드 + 읽기 전용 컨테이너 스모크 (health) | 병합 금지 |
| pipeline | uv sync --locked, ruff, pytest (80%), pip-audit | 병합 금지 |
| integration | 파이프라인 → 서버 실제 HTTP | 병합 금지 |
| app | Flutter 3.41.7: bootstrap, analyze, test, 데모 debug APK (14일 보관) | 병합 금지 |

- 배포 전략: 서버는 단일 인스턴스 재시작 배포 (`docker compose up -d --build`), 롤백 = 이전 커밋으로 재빌드 (API 는 필드 추가만이라 DB 호환)
- 도구 버전 고정: Python 3.12, uv 0.13.9, Flutter 3.41.7, cyclonedx-bom 7.2.1, Actions 는 메이저 태그 (커밋 SHA 고정은 저장소 생성 후 Dependabot 으로 권장)
