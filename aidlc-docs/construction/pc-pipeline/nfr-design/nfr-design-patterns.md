# NFR Design Patterns — pc-pipeline

| NFR | 패턴 | 위치 |
| --- | --- | --- |
| NFR-P01 | Strategy: `Provider.complete(system, user) -> str` 하나로 6종 구현, 팩토리 `make_provider(config)` | `providers.py` |
| NFR-P01 | 프롬프트 외부화: `prompts/*.md` 의 `{{자리}}` 치환 | `prompts/` |
| NFR-P02 | 배치 (10편씩), 상한 컷 | `analyze.py` |
| NFR-P03 | 모든 httpx 클라이언트에 시간 제한, CLI 는 `subprocess.run(timeout=)` | `hf_client.py`, `providers.py` |
| NFR-P04 | 재시도 (지수 대기) + 날짜 단위 중단, 업로드 전 계약 검사 | `retry.py`, `runner.py` |
| NFR-P05 | 비밀은 `config.secret()` 으로만 읽기, 로그 필터 없음 (애초에 넘기지 않음) | `config.py` |
| NFR-P06 | Anti-corruption layer: HF 응답 → `RawPaper` 변환에서 형식 검사 | `hf_client.py` |
| NFR-P08 | 의존성 주입 (httpx.Client, Provider, 시계) | `runner.py` |
