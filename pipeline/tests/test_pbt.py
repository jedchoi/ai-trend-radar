"""PBT (부분 적용): business-logic-model.md 의 속성."""

import datetime as dt
import json

from hypothesis import given
from hypothesis import strategies as st

from radar.analyze import extract_json, normalize_keywords
from radar.models import RawPaper, Topic
from radar.runner import plan_dates
from radar.select import select_featured

dates = st.dates(min_value=dt.date(2024, 1, 1), max_value=dt.date(2027, 12, 31))


@given(st.one_of(st.none(), dates), dates, st.one_of(st.none(), dates))
def test_plan_dates_properties(last, target, explicit):
    result = plan_dates(last, target, explicit)
    if explicit is not None:
        assert result == [explicit]
        return
    assert result == sorted(set(result))
    assert len(result) <= 7
    assert all(d <= target for d in result)
    if last is not None:
        assert all(d > last for d in result)


@given(st.lists(st.text(max_size=80), max_size=30))
def test_normalize_keywords_idempotent(words):
    once = normalize_keywords(words)
    assert normalize_keywords(once) == once
    assert len(once) <= 8
    assert all(w == w.lower() and 0 < len(w) <= 60 for w in once)


@given(st.lists(st.integers(min_value=0, max_value=500), max_size=30), st.integers(min_value=0, max_value=10))
def test_select_featured_count_and_order(upvotes, n):
    papers = [RawPaper(id=f"p{i}", title="t", upvotes=u) for i, u in enumerate(upvotes)]
    topics = {p.id: Topic.OTHER for p in papers}
    chosen = select_featured(papers, topics, n, set())
    assert len(chosen) == min(n, len(papers))
    picked = [p.upvotes for p in papers if p.id in chosen]
    rest = [p.upvotes for p in papers if p.id not in chosen]
    assert not picked or not rest or min(picked) >= max(rest)


json_values = st.recursive(
    st.one_of(st.integers(), st.text(max_size=10), st.booleans(), st.none()),
    lambda children: st.lists(children, max_size=4) | st.dictionaries(st.text(max_size=5), children, max_size=4),
    max_leaves=10,
)


@given(
    st.one_of(
        st.dictionaries(st.text(max_size=5), json_values, min_size=1, max_size=4),
        st.lists(json_values, min_size=1, max_size=4),
    ),
    st.sampled_from(["{}", "```json\n{}\n```", "Here you go:\n{}\nThanks!", "```\n{}\n```"]),
)
def test_extract_json_round_trip(value, wrapper):
    text = wrapper.replace("{}", json.dumps(value, ensure_ascii=False), 1)
    assert extract_json(text) == value
