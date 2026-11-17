"""radar backfill (BR-P19 ~ BR-P23): 지난 N 일을 실제 데이터로 채운다."""

import datetime as dt
import json

from radar.analyze import Analyzer
from radar.hf_client import HFClient
from radar.publish import ServerClient
from radar.runner import EXIT_FAILED, EXIT_OK, Runner
from tests.conftest import KST_NOON, FakeHF, FakeServer, ScriptedProvider, hf_item
from tests.test_analyze import HEADLINE, brief_responder, detail_responder


def trending():
    return {"models": [{"id": "a/m1", "likes": 1, "trendingScore": 9}], "datasets": [], "spaces": []}


def days_items(*dates):
    return {d: [hf_item(f"2611.{i:02d}{n:03d}", upvotes=n) for n in range(3)] for i, d in enumerate(dates)}


def build(config, hf, server, provider=None, sleeps=None):
    return Runner(
        config=config,
        hf=HFClient(hf.client(), sleep=lambda s: None),
        server=ServerClient(server.client(), token="secret-token-value", sleep=lambda s: None),
        analyzer=Analyzer(provider=provider, max_ai_papers=60),
        now=lambda: KST_NOON,
        sleep=(sleeps.append if sleeps is not None else (lambda s: None)),
    )


def ai():
    return ScriptedProvider(
        {
            "BRIEF": brief_responder,
            "DETAIL": detail_responder,
            "HEADLINE": lambda u: HEADLINE,
            "REPORT": lambda u: json.dumps({"narrative": "AI 리포트"}),
        }
    )


def test_backfill_uploads_fast_results_first_then_ai_newest_first(config):
    # BR-P20, BR-P21: 1단계 none 결과를 오래된 날부터 바로 올리고, 2단계 AI 결과를 최근 날부터 덮어쓴다
    hf = FakeHF(days=days_items("2026-11-14", "2026-11-15", "2026-11-16"), trending=trending())
    server = FakeServer()
    assert build(config, hf, server, provider=ai()).run_backfill(days=3) == EXIT_OK
    order = [(u["date"], u["provider"]) for u in server.uploads]
    assert order == [
        ("2026-11-14", "none"),
        ("2026-11-15", "none"),
        ("2026-11-16", "none"),
        ("2026-11-16", "fake"),
        ("2026-11-15", "fake"),
        ("2026-11-14", "fake"),
    ]
    by = {(u["date"], u["provider"]): u for u in server.uploads}
    # BR-P20: Hub 트렌딩은 지금 시점 목록이라 마지막 날에만 붙인다
    assert by[("2026-11-16", "none")]["hub"] and by[("2026-11-16", "fake")]["hub"]
    assert by[("2026-11-14", "none")]["hub"] == [] and by[("2026-11-14", "fake")]["hub"] == []
    assert all(p["summary_source"] == "ai" for p in by[("2026-11-15", "fake")]["papers"])
    state = json.loads((config.data_path / "analyzed.json").read_text())
    assert state == {"2026-11-14": "fake", "2026-11-15": "fake", "2026-11-16": "fake"}
    assert json.loads((config.data_path / "state.json").read_text())["last_success_date"] == "2026-11-16"


def test_backfill_without_ai_only_uploads_once(config):
    hf = FakeHF(days=days_items("2026-11-15", "2026-11-16"), trending=trending())
    server = FakeServer()
    assert build(config, hf, server).run_backfill(days=2) == EXIT_OK
    assert [(u["date"], u["provider"]) for u in server.uploads] == [("2026-11-15", "none"), ("2026-11-16", "none")]


def test_backfill_resumes_from_archive_and_skips_analyzed_days(config):
    # BR-P20, BR-P21: 다시 돌리면 보관본을 쓰고, AI 로 분석한 날은 건너뛴다 (중단 후 재개)
    hf = FakeHF(days=days_items("2026-11-15", "2026-11-16"), trending=trending())
    build(config, hf, FakeServer()).run_backfill(days=2)
    fetched = len([c for c in hf.calls if c.startswith("/api/daily_papers")])

    provider = ai()
    server = FakeServer()
    assert build(config, hf, server, provider=provider).run_backfill(days=2) == EXIT_OK
    assert len([c for c in hf.calls if c.startswith("/api/daily_papers")]) == fetched  # 다시 받지 않음
    assert [(u["date"], u["provider"]) for u in server.uploads] == [
        ("2026-11-15", "none"),
        ("2026-11-16", "none"),
        ("2026-11-16", "fake"),
        ("2026-11-15", "fake"),
    ]

    again = FakeServer()
    provider2 = ai()
    assert build(config, hf, again, provider=provider2).run_backfill(days=2, reports=False) == EXIT_OK
    assert again.uploads == []  # AI 결과를 none 으로 덮지 않고, 다시 분석하지도 않음
    assert provider2.calls == []


def test_backfill_stops_ai_when_provider_is_broken(config):
    # BR-P21: 한 날짜의 AI 호출이 모두 실패하면 제공자 문제로 보고 2단계를 멈춘다
    def boom(user):
        raise RuntimeError("not logged in")

    provider = ScriptedProvider({"BRIEF": boom, "DETAIL": boom, "HEADLINE": boom, "REPORT": boom})
    hf = FakeHF(days=days_items("2026-11-15", "2026-11-16"), trending=trending())
    server = FakeServer()
    assert build(config, hf, server, provider=provider).run_backfill(days=2, reports=False) == EXIT_FAILED
    assert [u["provider"] for u in server.uploads] == ["none", "none"]
    assert not (config.data_path / "analyzed.json").exists()
    briefs = [k for k, _ in provider.calls if k == "BRIEF"]
    assert len(briefs) == 2  # 첫 날짜 (1회 + 재시도 1회) 에서 멈춤


def test_backfill_continues_after_a_failed_day(config):
    # BR-P20: 하루 수집 실패는 기록하고 다음 날짜로 (날짜끼리 독립)
    hf = FakeHF(days=days_items("2026-11-14", "2026-11-16"), trending=trending(), fail_dates={"2026-11-15"})
    server = FakeServer()
    assert build(config, hf, server).run_backfill(days=3) == EXIT_FAILED
    assert [u["date"] for u in server.uploads] == ["2026-11-14", "2026-11-16"]
    runs = [json.loads(line) for line in (config.data_path / "runs.jsonl").read_text().splitlines()]
    assert any(r["date"] == "2026-11-15" and r["status"] == "failed" and r["stage"] == "collect" for r in runs)
    assert not (config.data_path / "state.json").exists()  # 빈 날이 있으면 last_success 를 올리지 않음


def test_backfill_auth_failure_aborts(config):
    hf = FakeHF(days=days_items("2026-11-15", "2026-11-16"), trending=trending())
    server = FakeServer(statuses=[401])
    assert build(config, hf, server).run_backfill(days=2) == EXIT_FAILED
    assert len(server.auth) == 1


def test_backfill_is_polite_to_hugging_face(config):
    # BR-P20: 새로 받는 날짜 사이 0.5초 쉬기
    sleeps = []
    hf = FakeHF(days=days_items("2026-11-15", "2026-11-16"), trending=trending())
    build(config, hf, FakeServer(), sleeps=sleeps).run_backfill(days=2, reports=False)
    assert sleeps == [0.5, 0.5]


def test_backfill_writes_reports_for_every_week_and_month(config):
    # BR-P22: 범위에 걸친 모든 주 · 월 리포트 (통계가 없으면 건너뜀)
    stats = {"paper_count": 3, "topics": [{"topic": "agents", "count": 3}], "rising_keywords": []}
    server = FakeServer(stats={"2026-W45": stats, "2026-W46": stats, "2026-11": stats})
    hf = FakeHF(days=days_items("2026-11-08", "2026-11-16"), trending=trending())
    assert build(config, hf, server).run_backfill(days=9) == EXIT_OK  # 11-08 (W45) ~ 11-16 (W47)
    keys = [(r["period"], r["key"]) for r in server.reports]
    assert keys == [("week", "2026-W45"), ("week", "2026-W46"), ("month", "2026-11")]  # W47 · 2026-10 없음 → 건너뜀
    assert all("에이전트" in r["narrative"] for r in server.reports)


def test_backfill_range_and_limits(config):
    # BR-P19
    server = FakeServer()
    runner = build(config, FakeHF(trending=trending()), server)
    assert runner.backfill_dates(days=3, until=None) == [
        dt.date(2026, 11, 14),
        dt.date(2026, 11, 15),
        dt.date(2026, 11, 16),
    ]
    assert runner.backfill_dates(days=2, until=dt.date(2026, 10, 2)) == [dt.date(2026, 10, 1), dt.date(2026, 10, 2)]


def test_backfill_uploads_news_before_slow_ai_phase(config):
    # 버그 (2026-11-18 사용자 보고 "뉴스는 비어있네"): 뉴스가 몇 시간 걸리는 AI 단계 뒤에야 올라갔다.
    # BR-P34 (수정): 1단계 직후 뉴스를 AI 없이 먼저 올리고, AI 단계 뒤에 AI 로 다시 분석해 덮어쓴다
    import dataclasses

    from tests.test_news import ARTICLE_HTML, FEED

    config = dataclasses.replace(config, collect=dataclasses.replace(config.collect, news=True))
    provider = ai()
    provider.responders["NEWS"] = lambda u: json.dumps(
        {"topic": "other", "summary": "AI 뉴스 요약", "key_points": [], "keywords": []}
    )
    pages = {"/blog/feed.xml": FEED, "/blog/ggml-org/llama-cpp-v1": ARTICLE_HTML}
    hf = FakeHF(days=days_items("2026-11-15", "2026-11-16"), trending=trending(), pages=pages)
    server = FakeServer()
    assert build(config, hf, server, provider=provider).run_backfill(days=5) == EXIT_OK  # 글 날짜 (11-12 ~ 13) 포함
    kinds = [(e[0], e[2]) for e in server.events]
    first_ai = kinds.index(("daily", "fake"))
    assert ("news", "none") in kinds[:first_ai]
    assert kinds.index(("news", "fake")) > first_ai
