# Code Generation 계획 — pc-pipeline

- 대상 story: US-16 ~ US-20, US-01 (세 줄), US-05 (상세 · 용어), US-02 (주제)
- 방식: TDD (RED → GREEN → REFACTOR), 외부 HTTP 는 `httpx.MockTransport`

## Steps

- [x] Step 1: 골격 — `pipeline/pyproject.toml` (의존성 고정, `radar` 명령), `uv.lock`
- [x] Step 2: 형식 — `radar/models.py` (서버 계약과 같은 필드)
- [x] Step 3 (RED): 테스트
  - `tests/test_selection.py`: BR-P04, BR-P05, BR-P06 (AC-01-2, AC-09-3)
  - `tests/test_hf_client.py`: BR-P02, BR-P03 (AC-16-1)
  - `tests/test_analyze.py`: BR-P07 ~ BR-P10 (AC-17-1, AC-17-2, AC-05-1, AC-05-3)
  - `tests/test_providers.py`: 6종 요청 형식 · 응답 해석 (AC-17-1, AC-17-3)
  - `tests/test_runner.py`: BR-P11 ~ BR-P18 (AC-16-1 ~ AC-16-3, AC-18-1, AC-18-2, AC-19-1, AC-20-1, AC-20-2)
  - `tests/test_pbt.py`: PBT 속성 (business-logic-model.md)
  - `tests/test_contract.py`: 결과가 서버 `DigestIngest` 를 통과 (server 가 있을 때)
- [x] Step 4 (GREEN): `config.py`, `retry.py`, `hf_client.py`, `topics.py`, `select.py`, `analyze.py`, `providers.py`, `prompts/*.md`, `publish.py`, `runner.py`, `cli.py`
- [x] Step 5 (REFACTOR): ruff
- [x] Step 6: 배포 파일 — `pipeline/deploy/run-daily.sh`, `com.jedchoi.ai-trend-radar.plist`, `install-mac.sh`, `config.example.toml`
- [x] Step 7: 코드 요약 문서
