# Logical Components — pc-pipeline

| 구성 요소 | 파일 |
| --- | --- |
| 설정 · 비밀 | `pipeline/radar/config.py` |
| 재시도 | `pipeline/radar/retry.py` |
| HF 수집 | `pipeline/radar/hf_client.py` |
| 주제 규칙 | `pipeline/radar/topics.py` |
| 선별 | `pipeline/radar/select.py` |
| JSON 추출 · 분석 | `pipeline/radar/analyze.py` |
| 제공자 | `pipeline/radar/providers.py` |
| 프롬프트 | `pipeline/radar/prompts/{brief,detail,headline,report}.md` |
| 서버 통신 | `pipeline/radar/publish.py` |
| 실행 · 상태 · 기록 | `pipeline/radar/runner.py` |
| 명령 | `pipeline/radar/cli.py` |
| 형식 | `pipeline/radar/models.py` |
