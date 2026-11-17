"""PBT (부분 적용): 순수 함수 · 직렬화 왕복 (business-logic-model.md 의 속성 표)."""

import datetime as dt

from hypothesis import given, settings
from hypothesis import strategies as st

from app.periods import period_key, period_range, previous_periods, rising_keywords, streak
from app.schemas import DigestIngest, Topic

dates = st.dates(min_value=dt.date(2021, 1, 1), max_value=dt.date(2030, 12, 31))
periods = st.sampled_from(["week", "month"])


@given(periods, dates)
def test_period_key_round_trip(period, day):
    # PBT-02: 날짜 → key → 범위 → 범위 안 모든 날짜의 key 가 같다
    key = period_key(period, day)
    start, end = period_range(period, key)
    assert start <= day <= end
    assert period_key(period, start) == key
    assert period_key(period, end) == key
    if period == "week":
        assert (end - start).days == 6
        assert start.weekday() == 0


@given(periods, dates, st.integers(min_value=1, max_value=8))
def test_previous_periods_are_contiguous(period, day, n):
    # PBT-03: n 개, 연속 · 겹치지 않음, 마지막 end + 1 = key 의 start
    key = period_key(period, day)
    prev = previous_periods(period, key, n)
    assert len(prev) == n
    ranges = [period_range(period, k) for k in prev]
    for (_, end_a), (start_b, _) in zip(ranges, ranges[1:], strict=False):
        assert end_a + dt.timedelta(days=1) == start_b
    assert ranges[-1][1] + dt.timedelta(days=1) == period_range(period, key)[0]


keywords = st.text(alphabet="abcdefgh", min_size=1, max_size=4)


@given(
    st.dictionaries(keywords, st.integers(min_value=0, max_value=30), max_size=30),
    st.dictionaries(keywords, st.floats(min_value=0, max_value=30), max_size=30),
)
def test_rising_keywords_invariants(counts, baselines):
    # PBT-03: 결과는 count ≥ 3, ratio ≥ 2, 최대 10개, ratio 내림차순
    result = rising_keywords(counts, baselines)
    assert len(result) <= 10
    assert all(r.count >= 3 and r.ratio >= 2.0 for r in result)
    ratios = [r.ratio for r in result]
    assert ratios == sorted(ratios, reverse=True)


@given(st.sets(dates, max_size=40), dates)
def test_streak_bounds(present, day):
    # PBT-03: day 가 있으면 1 ≤ streak ≤ len, 없으면 0
    result = streak(present, day)
    if day in present:
        assert 1 <= result <= len(present)
        assert all(day - dt.timedelta(days=i) in present for i in range(result))
    else:
        assert result == 0


paper_ids = st.from_regex(r"[0-9]{4}\.[0-9]{5}", fullmatch=True)
safe_text = st.text(
    alphabet=st.characters(min_codepoint=0x41, max_codepoint=0xD7A3, blacklist_categories=("Cs", "Cc")),
    min_size=1,
    max_size=40,
)


@settings(max_examples=60)
@given(
    st.lists(
        st.tuples(paper_ids, safe_text, st.sampled_from(list(Topic)), st.integers(0, 500)),
        max_size=8,
        unique_by=lambda t: t[0],
    ),
    st.dates(min_value=dt.date(2021, 1, 1), max_value=dt.date(2026, 11, 1)),
)
def test_digest_json_round_trip(rows, day):
    # PBT-02: DigestIngest → JSON → DigestIngest 동일
    papers = [
        {"id": pid, "title": title.strip() or "t", "topic": topic.value, "one_liner": "x", "upvotes": up}
        for pid, title, topic, up in rows
    ]
    digest = DigestIngest.model_validate({"date": day.isoformat(), "papers": papers})
    again = DigestIngest.model_validate_json(digest.model_dump_json())
    assert again == digest
