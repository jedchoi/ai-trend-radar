"""논문 원문 (FR-26, BR-P31): 주목 논문 본문 · Hugging Face 원본 JSON."""

import dataclasses
import json

from radar.analyze import Analyzer
from radar.hf_client import HFClient, parse_daily_item
from radar.publish import ServerClient
from radar.runner import EXIT_OK, Runner
from tests.conftest import KST_NOON, FakeHF, FakeServer, hf_item


def runner_for(config, hf, server):
    sleeps = []
    runner = Runner(
        config=dataclasses.replace(config, collect=dataclasses.replace(config.collect, full_text=True)),
        hf=HFClient(hf.client(), sleep=lambda s: None),
        server=ServerClient(server.client(), token="t", sleep=lambda s: None),
        analyzer=Analyzer(),
        now=lambda: KST_NOON,
        sleep=sleeps.append,
    )
    return runner, sleeps


def test_source_raw_keeps_original_item():
    item = hf_item("2611.00001", numComments=3)
    raw = parse_daily_item(item)
    assert raw.source_raw == item


def test_source_raw_dropped_when_huge():
    item = hf_item("2611.00001", summary="x" * 150_000)
    assert parse_daily_item(item).source_raw is None


def test_featured_papers_carry_full_text_and_cache(config):
    day = "2026-11-16"
    items = [hf_item("2611.00001", upvotes=90, ai_keywords=["agent"]), hf_item("2611.00002", upvotes=1)]
    hf = FakeHF(days={day: items}, markdown={"2611.00001": "# Title\n\nFull body"})
    server = FakeServer()
    runner, sleeps = runner_for(config, hf, server)
    assert runner.run_daily(backfill=False) == EXIT_OK
    papers = {p["id"]: p for p in server.uploads[0]["papers"]}
    assert papers["2611.00001"]["full_text"] == "# Title\n\nFull body"
    assert papers["2611.00001"]["source_raw"]["paper"]["id"] == "2611.00001"
    featured_without_text = [p for p in papers.values() if p["featured"] and p["id"] != "2611.00001"]
    assert all(p["full_text"] is None for p in featured_without_text)
    assert all(p["full_text"] is None for p in papers.values() if not p["featured"])
    assert 3.0 in sleeps  # NFR-10
    calls = len(hf.calls)
    assert runner.run_daily(explicit=__import__("datetime").date(2026, 11, 16)) == EXIT_OK
    md_calls = [c for c in hf.calls[calls:] if c.startswith("/papers/")]
    assert md_calls == []  # 보관본 사용 (없던 것도 다시 묻지 않음)


def test_full_text_failure_only_empties_text(config):
    day = "2026-11-16"
    hf = FakeHF(days={day: [hf_item("2611.00001", upvotes=90)]}, fail={"/papers/2611.00001.md": [500] * 10})
    server = FakeServer()
    runner, _ = runner_for(config, hf, server)
    assert runner.run_daily(backfill=False) == EXIT_OK
    assert server.uploads[0]["papers"][0]["full_text"] is None


def test_payload_with_full_text_matches_contract(config, contract):
    day = "2026-11-16"
    hf = FakeHF(days={day: [hf_item("2611.00001", upvotes=90)]}, markdown={"2611.00001": "body"})
    server = FakeServer()
    runner, _ = runner_for(config, hf, server)
    runner.run_daily(backfill=False)
    contract.DigestIngest.model_validate(json.loads(json.dumps(server.uploads[0])))
