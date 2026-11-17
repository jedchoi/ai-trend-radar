# Business Logic Model — pc-pipeline

```text
radar daily [--date D] [--no-backfill] [--dry-run --out F]
  check_config (BR-P11) ─ 실패 → exit 3
  dates = plan_dates(state, target, --date)                    # BR-P01, BR-P14
  for day in dates (오래된 순):
      raw    = hf.daily_papers(day); hub = hf.trending(...)    # BR-P02, BR-P03 → raw/{day}.json
      ranked = selector(raw)                                   # BR-P04, BR-P05
      result = analyzer.analyze_day(raw, featured, provider)   # BR-P06 ~ BR-P10
      payload = DigestPayload(...) 검사                         # 계약
      server.upload_digest(payload) ─ 실패 → 기록 후 중단       # BR-P12, BR-P18
      state.last_success = day; runs.jsonl += 기록              # BR-P13, BR-P16
  run_reports(today)                                           # BR-P17
```

## 순수 함수 (PBT 대상, 부분 적용)

| 함수 | 속성 |
| --- | --- |
| `plan_dates(last, target, explicit)` | 결과는 오름차순 · 중복 없음 · 최대 7개 · 모두 ≤ target · 모두 > last |
| `normalize_keywords(list)` | 멱등 (두 번 적용 = 한 번), 최대 8개, 모두 소문자 |
| `select_featured(papers, n)` | 결과 수 = min(n, 논문 수), 점수 상위만 |
| `extract_json(text)` | 코드 블록 · 앞뒤 설명이 붙어도 같은 JSON 을 꺼낸다 (왕복: dumps → 감싸기 → extract = 원래 값) |
| `DigestPayload` JSON 왕복 | dumps → loads 동일 |
