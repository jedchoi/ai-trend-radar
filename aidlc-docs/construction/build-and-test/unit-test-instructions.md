# Unit Test Instructions

| Unit | 명령 | 2026-11-17 결과 |
| --- | --- | --- |
| backend-server | `cd server && pytest --cov=app --cov-fail-under=80` | 71 passed, 96% |
| pc-pipeline | `cd pipeline && uv run pytest --cov=radar --cov-fail-under=80` | 83 passed, 94% |
| mobile-app | `cd app && flutter test` | 미실행 (Flutter 없음), CI 에서 실행 |

PBT (부분): `server/tests/test_periods_pbt.py`, `pipeline/tests/test_pbt.py` (hypothesis).
