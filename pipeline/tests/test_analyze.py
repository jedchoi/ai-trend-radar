import datetime as dt
import json

import pytest

from radar.analyze import Analyzer, extract_json, none_headline, none_paper
from radar.models import HubItem, RawPaper, Topic
from tests.conftest import ScriptedProvider

DAY = dt.date(2026, 11, 13)


def raw(pid, **kw) -> RawPaper:
    return RawPaper(
        id=pid,
        title=kw.pop("title", f"Paper {pid}"),
        abstract=kw.pop("abstract", "First. Second."),
        ai_summary=kw.pop("ai_summary", f"HF summary {pid}"),
        ai_keywords=kw.pop("kw", ["RL"]),
        **kw,
    )


def brief_responder(user: str) -> str:
    ids = [p["id"] for p in json.loads(user.split("PAPERS_JSON:", 1)[1])]
    return json.dumps({"papers": [{"id": i, "topic": "agents", "one_liner": f"{i} 한국어 요약"} for i in ids]})


def detail_responder(user: str) -> str:
    pid = user.split("ID:", 1)[1].split()[0]
    return (
        "```json\n"
        + json.dumps(
            {
                "id": pid,
                "topic": "agents",
                "one_liner": f"{pid} 상세 한 줄",
                "what": "무엇",
                "novelty": "새로움",
                "why": "중요",
                "apply": "적용",
                "glossary": [{"term": "RL", "explanation": "강화학습"}],
            },
            ensure_ascii=False,
        )
        + "\n```"
    )


HEADLINE = json.dumps({"headline": ["하나", "둘", "셋"]})


def test_extract_json_handles_fences_and_prose():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! Here it is: {"a": [1, 2]} hope this helps') == {"a": [1, 2]}
    assert extract_json("[1, 2]") == [1, 2]
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_none_paper_uses_hf_summary_then_abstract():
    # BR-P07
    p = none_paper(raw("1", kw=["Agent", "agent"]), Topic.AGENTS, featured=True)
    assert (p.one_liner, p.summary_source, p.keywords, p.detail) == ("HF summary 1", "hf", ["agent"], None)
    q = none_paper(raw("2", ai_summary=None, abstract="We do X. Then Y."), Topic.OTHER, featured=False)
    assert (q.one_liner, q.summary_source) == ("We do X.", "abstract")
    r = none_paper(raw("3", ai_summary="", abstract=""), Topic.OTHER, featured=False)
    assert r.one_liner == "Paper 3"


def test_none_paper_truncates_long_summary():
    p = none_paper(raw("1", ai_summary="가" * 500), Topic.OTHER, featured=False)
    assert len(p.one_liner) == 400


def test_none_headline_from_featured():
    # BR-P07: 주목 상위 3편 "제목 — 요약"
    papers = [none_paper(raw(str(i)), Topic.OTHER, featured=True) for i in range(4)]
    assert none_headline(papers) == [f"Paper {i} — HF summary {i}" for i in range(3)]
    assert none_headline([]) == []


def test_none_provider_day():
    # AC-17-1: 키 없이 전체 결과, featured 표시, 세 줄
    analyzer = Analyzer(provider=None, max_ai_papers=60)
    raws = [raw("1", upvotes=5), raw("2", upvotes=9)]
    topics = {"1": Topic.OTHER, "2": Topic.AGENTS}
    payload, fallbacks = analyzer.analyze_day(DAY, raws, topics, ["2"], [])
    assert payload.provider == "none"
    assert fallbacks == 0
    assert [(p.id, p.featured, p.topic) for p in payload.papers] == [("1", False, "other"), ("2", True, "agents")]
    assert payload.headline == ["Paper 2 — HF summary 2"]


def test_ai_provider_day_full_results():
    # BR-P08: 모든 논문 한 줄 · 주제, 주목 논문 상세 · 용어, 세 줄
    provider = ScriptedProvider({"BRIEF": brief_responder, "DETAIL": detail_responder, "HEADLINE": [HEADLINE]})
    analyzer = Analyzer(provider=provider, max_ai_papers=60, markdown=lambda pid: f"FULL TEXT {pid}")
    raws = [raw(f"2611.{i:05d}", upvotes=i) for i in range(12)]
    topics = {r.id: Topic.OTHER for r in raws}
    hub = [HubItem(kind="model", rank=1, id="a/b")]
    payload, fallbacks = analyzer.analyze_day(DAY, raws, topics, ["2611.00011"], hub)
    assert fallbacks == 0
    assert payload.provider == "fake"
    assert payload.headline == ["하나", "둘", "셋"]
    assert payload.hub == hub
    by_id = {p.id: p for p in payload.papers}
    assert by_id["2611.00003"].one_liner == "2611.00003 한국어 요약"
    assert by_id["2611.00003"].summary_source == "ai"
    featured = by_id["2611.00011"]
    assert featured.detail.apply == "적용"
    assert featured.glossary[0].term == "RL"
    assert featured.one_liner == "2611.00011 상세 한 줄"
    kinds = [k for k, _ in provider.calls]
    assert kinds.count("BRIEF") == 2  # 12편 → 10편씩 2회
    assert kinds.count("DETAIL") == 1
    detail_prompt = next(u for k, u in provider.calls if k == "DETAIL")
    assert "FULL TEXT 2611.00011" in detail_prompt


def test_ai_cap_uses_none_for_the_rest():
    # BR-P09: 추천 수 상위 max_ai_papers 편만 AI
    provider = ScriptedProvider({"BRIEF": brief_responder, "DETAIL": detail_responder, "HEADLINE": [HEADLINE]})
    analyzer = Analyzer(provider=provider, max_ai_papers=2)
    raws = [raw("a", upvotes=1), raw("b", upvotes=50), raw("c", upvotes=30)]
    payload, _ = analyzer.analyze_day(DAY, raws, dict.fromkeys(["a", "b", "c"], Topic.OTHER), [], [])
    sources = {p.id: p.summary_source for p in payload.papers}
    assert sources == {"a": "hf", "b": "ai", "c": "ai"}


def test_invalid_response_is_retried_once_then_succeeds():
    # BR-P10: 형식 위반 → 1회 재요청
    responses = ["not json", json.dumps({"papers": [{"id": "a", "topic": "agents", "one_liner": "ok"}]})]
    provider = ScriptedProvider({"BRIEF": responses, "HEADLINE": [HEADLINE]})
    payload, fallbacks = Analyzer(provider=provider, max_ai_papers=60).analyze_day(
        DAY, [raw("a")], {"a": Topic.OTHER}, [], []
    )
    assert payload.papers[0].one_liner == "ok"
    assert fallbacks == 0
    assert "형식" in provider.calls[1][1]  # 재요청에 형식 안내를 붙인다


def test_items_still_invalid_after_retry_fall_back_individually():
    # BR-P10 / AC-17-2: 다시 실패한 항목만 none 결과
    bad_topic = json.dumps(
        {
            "papers": [
                {"id": "a", "topic": "agents", "one_liner": "ok"},
                {"id": "b", "topic": "crypto", "one_liner": "bad"},
            ]
        }
    )
    still_bad = json.dumps({"papers": [{"id": "b", "topic": "crypto", "one_liner": "bad"}]})
    provider = ScriptedProvider({"BRIEF": [bad_topic, still_bad], "HEADLINE": [HEADLINE]})
    payload, fallbacks = Analyzer(provider=provider, max_ai_papers=60).analyze_day(
        DAY, [raw("a"), raw("b")], {"a": Topic.OTHER, "b": Topic.SPEECH_AUDIO}, [], []
    )
    by_id = {p.id: p for p in payload.papers}
    assert (by_id["a"].summary_source, by_id["a"].topic) == ("ai", "agents")
    assert (by_id["b"].summary_source, by_id["b"].topic, by_id["b"].one_liner) == ("hf", "speech-audio", "HF summary b")
    assert fallbacks == 1


def test_provider_exception_falls_back():
    # BR-P10: 제공자 오류도 대체
    def boom(user):
        raise RuntimeError("timeout")

    provider = ScriptedProvider({"BRIEF": boom, "DETAIL": boom, "HEADLINE": boom})
    payload, fallbacks = Analyzer(provider=provider, max_ai_papers=60).analyze_day(
        DAY, [raw("a")], {"a": Topic.OTHER}, ["a"], []
    )
    assert payload.papers[0].summary_source == "hf"
    assert payload.headline == ["Paper a — HF summary a"]
    assert fallbacks == 3  # brief 1 + detail 1 + headline 1


def test_detail_failure_keeps_brief_result():
    provider = ScriptedProvider({"BRIEF": brief_responder, "DETAIL": ["{}", "{}"], "HEADLINE": [HEADLINE]})
    payload, fallbacks = Analyzer(provider=provider, max_ai_papers=60).analyze_day(
        DAY, [raw("a")], {"a": Topic.OTHER}, ["a"], []
    )
    paper = payload.papers[0]
    assert paper.featured and paper.detail is None
    assert paper.one_liner == "a 한국어 요약"
    assert fallbacks == 1


def test_zero_papers_day_has_no_headline_and_no_ai_calls():
    # BR-P15
    provider = ScriptedProvider({})
    payload, _ = Analyzer(provider=provider, max_ai_papers=60).analyze_day(DAY, [], {}, [], [])
    assert payload.papers == [] and payload.headline == []
    assert provider.calls == []


def test_narrative_ai_and_none():
    # BR-P17
    stats = {
        "key": "2026-W46",
        "paper_count": 40,
        "topics": [{"topic": "agents", "count": 12}, {"topic": "llm-reasoning", "count": 9}],
        "rising_keywords": [{"keyword": "memory", "ratio": 4.0}, {"keyword": "moe", "ratio": 3.0}],
    }
    provider = ScriptedProvider({"REPORT": [json.dumps({"narrative": "이번 주 요약 문장."})]})
    assert Analyzer(provider=provider, max_ai_papers=1).narrative("week", stats) == "이번 주 요약 문장."
    text = Analyzer(provider=None, max_ai_papers=1).narrative("week", stats)
    assert "40편" in text and "에이전트" in text and "memory" in text
    assert "이번 주" in text
    month = Analyzer(provider=None, max_ai_papers=1).narrative("month", {**stats, "rising_keywords": []})
    assert "이번 달" in month and "급상승" not in month
