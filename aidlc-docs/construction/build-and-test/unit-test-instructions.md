# Unit Test Instructions

| Unit | 명령 | 2026-11-17 결과 |
| --- | --- | --- |
| backend-server | `cd server && pytest --cov=app --cov-fail-under=80` | 71 passed, 96% |
| pc-pipeline | `cd pipeline && uv run pytest --cov=radar --cov-fail-under=80` | 85 passed, 94% (dry-run 수정 후) |
| mobile-app | `cd app && flutter test` | 40 passed (사용자 Mac, Flutter, 2026-11-17) |

PBT (부분): `server/tests/test_periods_pbt.py`, `pipeline/tests/test_pbt.py` (hypothesis).
