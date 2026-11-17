# Business Logic Model — backend-server

## 업로드 흐름 (POST /api/v1/ingest/daily)

1. Middleware: 요청 속도 확인 (ingest 분당 30회) → 초과 429
2. Ingest Auth: BR-S01 → 401 / 503
3. Schema 검사: BR-S04 → 422
4. Repository.upsert_digest: BR-S02 · BR-S03 트랜잭션, ingest_log 1행 추가
5. 응답 `{date, papers}`

## 조회 흐름

- `GET /digests/{date}`: 날짜 형식 검사 → digest 조회 (없으면 404) → 논문 정렬 (BR-S06) → Hub 에 is_new · streak_days 계산 (BR-S07, BR-S08)
- `GET /papers/{id}`: 상세 + 관련 논문 (BR-S09)
- `GET /papers?...`: 검색 (BR-S10, BR-S11)

## 트렌드 계산 (Trend Service)

```text
period_stats(period, key):
  [start, end] = 기간 범위 (BR-S12)
  prev = 직전 기간 1개, base = 직전 기간 4개
  topics = 주제별 count(start..end), prev_count(prev)            # BR-S13
  ready  = earliest_digest_date <= base[0].start                  # BR-S15
  rising = keyword count vs avg(base) 규칙 (ready 일 때만)        # BR-S14
  top    = upvotes 상위 5                                         # BR-S16
  hub_new, hub_steady                                             # BR-S17, BR-S18
  narrative = reports(period, key)
```

순수 함수로 분리: 기간 계산 (`period_range`, `previous_periods`), 급상승 판정 (`rising_keywords(counts, baselines)`), 연속 일수 (`streak(dates, day)`). 이 함수들은 PBT 대상 (PBT 부분 적용).

## 테스트 가능한 속성 (PBT-01)

| 함수 | 속성 |
| --- | --- |
| `period_range(key)` / `period_key(date)` | 왕복: 기간 안의 모든 날짜의 key 는 원래 key, start ≤ end, 주는 7일 |
| `previous_periods(key, n)` | n 개, 서로 겹치지 않고 연속, 마지막 것의 end + 1일 = key 의 start |
| `rising_keywords` | 결과의 모든 항목이 count ≥ 3 · ratio ≥ 2, 최대 10개, ratio 내림차순 |
| `streak(dates, day)` | 1 ≤ 결과 ≤ len(dates) (day 포함 시), day 가 없으면 0 |
| Schema JSON 왕복 | `DigestIngest` → JSON → `DigestIngest` 가 같다 |
