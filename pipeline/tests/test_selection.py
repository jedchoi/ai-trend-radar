import datetime as dt

from radar.analyze import normalize_keywords
from radar.models import RawPaper, Topic
from radar.select import score, select_featured
from radar.topics import classify


def raw(pid, **kw) -> RawPaper:
    return RawPaper(id=pid, title=kw.pop("title", f"Paper {pid}"), **kw)


def test_classify_uses_title_keywords_and_abstract():
    # BR-P04: 제목 · 키워드 2점, 초록 1점
    assert classify("Tool-using LLM agents for web tasks", [], "") == Topic.AGENTS
    assert classify("A new model", ["text-to-speech"], "") == Topic.SPEECH_AUDIO
    assert classify("A new model", [], "We propose a video diffusion model.") == Topic.IMAGE_VIDEO_GEN


def test_classify_tie_breaks_by_topic_order_and_defaults_to_other():
    # BR-P04: 동점은 주제 순서, 0점은 other
    assert classify("Reasoning agents", [], "") == Topic.LLM_REASONING
    assert classify("Untitled", [], "Nothing relevant here.") == Topic.OTHER


def test_classify_only_reads_first_600_chars_of_abstract():
    # BR-P04: 초록 앞 600자
    abstract = "x " * 400 + "robot manipulation"
    assert classify("Untitled", [], abstract) == Topic.OTHER


def test_score_adds_focus_and_code_bonus():
    # BR-P05: 추천 수 + 30 (focus) + 15 (GitHub)
    paper = raw("1", upvotes=10, github_url="https://github.com/a/b")
    assert score(paper, Topic.AGENTS, {Topic.AGENTS}) == 55
    assert score(paper, Topic.OTHER, {Topic.AGENTS}) == 25
    assert score(raw("2", upvotes=3), Topic.OTHER, set()) == 3


def test_select_featured_top_n_with_tie_breaks():
    # BR-P05: 점수 → 추천 수 → id
    papers = [raw("a", upvotes=50), raw("b", upvotes=20), raw("c", upvotes=20), raw("d", upvotes=5)]
    topics = {"a": Topic.OTHER, "b": Topic.OTHER, "c": Topic.OTHER, "d": Topic.AGENTS}
    assert select_featured(papers, topics, 3, {Topic.AGENTS}) == ["a", "d", "b"]


def test_select_featured_when_fewer_papers_than_n():
    assert select_featured([raw("a")], {"a": Topic.OTHER}, 5, set()) == ["a"]
    assert select_featured([], {}, 5, set()) == []


def test_normalize_keywords():
    # BR-P06: 소문자 · 공백 정리 · 중복 제거 · 최대 8개
    assert normalize_keywords(["  Mixture  of Experts ", "mixture of experts", "RL", ""]) == [
        "mixture of experts",
        "rl",
    ]
    assert len(normalize_keywords([f"k{i}" for i in range(20)])) == 8
    assert normalize_keywords(["x" * 100]) == ["x" * 60]


def test_raw_paper_dates():
    assert raw("1", published_at=dt.date(2026, 1, 1)).published_at.year == 2026
