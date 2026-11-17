# Integration Test Instructions

- 명령: `PYTHONPATH=server:pipeline pytest integration -q` (또는 `tool/check.sh`)
- 내용: uvicorn 으로 서버를 실제 포트에 띄우고, 가짜 Hugging Face 응답으로 파이프라인 `run_daily` → 실제 HTTP 업로드 → 앱이 쓰는 조회 · 검색 · 트렌드 API 확인, 응답 키가 `contract/samples` 와 같은지, 같은 날짜 재실행 멱등, 틀린 토큰 401
- 결과 (2026-11-17): 2 passed
