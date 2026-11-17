# Security Test Instructions

| 항목 | 위치 | 결과 |
| --- | --- | --- |
| 토큰 없음 · 틀림 · 미설정 (401 · 503) | `server/tests/test_ingest.py` | 통과 |
| 보안 헤더 · 속도 제한 · 본문 크기 · 문서 화면 끔 · 일반 오류 응답 · 보안 이벤트 로그 (토큰 미기록) | `server/tests/test_security.py` | 통과 |
| FTS 질의 주입 문자 | `server/tests/test_papers.py::test_search_special_characters_are_safe` | 통과 |
| 비밀 미기록 (실행 기록) | `pipeline/tests/test_runner.py::test_run_record_line` | 통과 |
| http 서버 주소 거부 | `pipeline/tests/test_config_cli.py` | 통과 |
| 의존성 취약점 | `pip-audit -r server/requirements.txt` | 알려진 취약점 없음 |
| SBOM | CI `cyclonedx-py` | CI 산출물 |
