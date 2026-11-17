import datetime as dt

import httpx
import pytest

from radar.hf_client import HFClient, HFError
from tests.conftest import FakeHF, hf_item

DAY = dt.date(2026, 11, 13)


def make(fake: FakeHF) -> HFClient:
    return HFClient(fake.client(), sleep=lambda s: None)


def test_daily_papers_pages_of_ten_until_short_page():
    # BR-P02: limit=10, p=0.. 10편 미만이면 멈춤
    fake = FakeHF(days={"2026-11-13": [hf_item(f"2611.{i:05d}") for i in range(23)]})
    papers = make(fake).daily_papers(DAY)
    assert len(papers) == 23
    pages = [c for c in fake.calls if c.startswith("/api/daily_papers")]
    assert len(pages) == 3
    assert all("limit=10" in c and "date=2026-11-13" in c for c in pages)


def test_daily_papers_exact_multiple_needs_one_more_page():
    fake = FakeHF(days={"2026-11-13": [hf_item(f"2611.{i:05d}") for i in range(10)]})
    assert len(make(fake).daily_papers(DAY)) == 10
    assert len(fake.calls) == 2


def test_daily_papers_stops_at_twenty_pages():
    # BR-P02: 최대 20페이지
    fake = FakeHF(days={"2026-11-13": [hf_item(f"2611.{i:05d}") for i in range(300)]})
    assert len(make(fake).daily_papers(DAY)) == 200


def test_daily_paper_fields_are_parsed():
    item = hf_item(
        "2611.15777",
        title="SO-Arena",
        upvotes=85,
        ai_keywords=["System One", "benchmark"],
        github="https://github.com/holdrain/SO-Arena",
        stars=120,
        project="https://example.github.io/so",
        organization={"name": "nus", "fullname": "NUS"},
    )
    paper = make(FakeHF(days={"2026-11-13": [item]})).daily_papers(DAY)[0]
    assert paper.id == "2611.15777"
    assert paper.authors == ["Kim", "Lee"]
    assert paper.upvotes == 85
    assert paper.ai_keywords == ["System One", "benchmark"]
    assert paper.github_url == "https://github.com/holdrain/SO-Arena"
    assert paper.github_stars == 120
    assert paper.organization == "NUS"
    assert paper.published_at == dt.date(2026, 11, 11)


def test_malformed_items_are_skipped():
    # NFR-P06: 형식이 틀린 항목은 버린다
    items = [hf_item("2611.00001"), {"paper": {"id": "bad id!", "title": "x"}}, {"nothing": 1}, "string"]
    assert [p.id for p in make(FakeHF(days={"2026-11-13": items})).daily_papers(DAY)] == ["2611.00001"]


def test_retries_on_server_errors_then_succeeds():
    # BR-P02: 429 · 5xx 는 최대 3회 시도
    sleeps = []
    fake = FakeHF(days={"2026-11-13": [hf_item("2611.00001")]}, fail={"/api/daily_papers": [503, 429]})
    client = HFClient(fake.client(), sleep=sleeps.append)
    assert len(client.daily_papers(DAY)) == 1
    assert sleeps == [2, 4]


def test_gives_up_after_three_attempts():
    fake = FakeHF(fail={"/api/daily_papers": [500, 500, 500]})
    with pytest.raises(HFError):
        make(fake).daily_papers(DAY)


def test_client_error_is_not_retried():
    fake = FakeHF(fail={"/api/daily_papers": [400]})
    with pytest.raises(HFError):
        make(fake).daily_papers(DAY)
    assert len(fake.calls) == 1


def test_network_error_is_retried():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) < 3:
            raise httpx.ConnectError("down")
        return httpx.Response(200, json=[])

    client = HFClient(
        httpx.Client(transport=httpx.MockTransport(handler), base_url="https://huggingface.co"), sleep=lambda s: None
    )
    assert client.daily_papers(DAY) == []
    assert len(attempts) == 3


def test_trending_by_kind_with_rank():
    # BR-P03: trendingScore 내림차순, 개수 제한, 순위 부여
    fake = FakeHF(
        trending={
            "models": [
                {
                    "id": "Qwen/Qwen3.8-Flash-Next",
                    "likes": 4502,
                    "downloads": 158598,
                    "trendingScore": 4286,
                    "pipeline_tag": "image-text-to-text",
                },
                {"id": "zai-org/GLM-5.3-Flash", "likes": 1798, "trendingScore": 1694},
                {"id": "third/model", "likes": 1, "trendingScore": 1},
            ],
            "datasets": [{"id": "nvidia/simready-assets", "likes": 1187, "downloads": 1121844, "trendingScore": 802}],
            "spaces": [
                {"id": "not-a-repo-id", "likes": 1},
                {"id": "pollen-robotics/microduck-simulator", "likes": 455, "trendingScore": 182, "sdk": "gradio"},
            ],
        }
    )
    client = make(fake)
    models = client.trending("model", 2)
    assert [(m.rank, m.id, m.task) for m in models] == [
        (1, "Qwen/Qwen3.8-Flash-Next", "image-text-to-text"),
        (2, "zai-org/GLM-5.3-Flash", None),
    ]
    assert any("sort=trendingScore" in c and "direction=-1" in c and "limit=2" in c for c in fake.calls)
    assert client.trending("dataset", 5)[0].downloads == 1121844
    spaces = client.trending("space", 5)
    assert [(s.rank, s.id) for s in spaces] == [(1, "pollen-robotics/microduck-simulator")]


def test_paper_markdown_truncated_or_none():
    fake = FakeHF(markdown={"2611.00001": "# Title\n" + "a" * 50})
    client = make(fake)
    assert client.paper_markdown("2611.00001", max_chars=20) == ("# Title\n" + "a" * 50)[:20]
    assert client.paper_markdown("2611.99999") is None
