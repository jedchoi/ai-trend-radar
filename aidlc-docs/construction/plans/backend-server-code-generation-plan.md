# Code Generation 계획 — backend-server

- 대상 story: US-01 ~ US-03, US-05 ~ US-07, US-09 ~ US-12, US-19, US-20 (서버 부분)
- 방식: TDD (RED → GREEN → REFACTOR). RED 는 business-rules · nfr-requirements 만 보고 작성
- 코드 위치: `server/` (workspace 루트 기준), `contract/samples/`

## Steps

- [x] Step 1: 프로젝트 골격 — `server/requirements.txt` (고정 버전), `server/requirements-dev.txt`, `server/pyproject.toml` (ruff · pytest 설정)
- [x] Step 2: 계약 — `server/app/schemas.py` (BR-S04, NFR-S06, AC-19-3)
- [x] Step 3 (RED): 테스트 작성 · 실패 확인
  - `tests/test_ingest.py`: AC-19-1, AC-19-2, AC-19-3, AC-20-1 (BR-S01 ~ BR-S04, BR-S21)
  - `tests/test_digests.py`: AC-01-1 ~ AC-01-3, AC-02-2, AC-03-1, AC-03-2 (BR-S05 ~ BR-S08, BR-S22)
  - `tests/test_papers.py`: AC-05-1, AC-06-2, AC-07-1, AC-12-1 ~ AC-12-3 (BR-S09 ~ BR-S11)
  - `tests/test_trends.py`: AC-09-1 ~ AC-09-5, AC-10-1, AC-11-1 (BR-S12 ~ BR-S20)
  - `tests/test_periods_pbt.py`: PBT 속성 5개 (business-logic-model.md)
  - `tests/test_security.py`: NFR-S05 ~ NFR-S09
- [x] Step 4 (GREEN): `periods.py`, `repository.py`, `trends.py`, `security.py`, `middleware.py`, `routes_public.py`, `routes_ingest.py`, `config.py`, `logging_setup.py`, `main.py`
- [x] Step 5 (REFACTOR): 중복 정리, ruff 통과
- [x] Step 6: 성능 테스트 `tests/test_perf.py` (NFR-S01, `-m perf`)
- [x] Step 7: 예시 응답 생성 `server/tools/make_samples.py` → `contract/samples/*.json` (mobile-app 테스트 입력)
- [x] Step 8: `server/Dockerfile`, `.dockerignore`
- [x] Step 9: 코드 요약 `aidlc-docs/construction/backend-server/code/code-summary.md`
