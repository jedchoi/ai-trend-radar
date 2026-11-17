"""뉴스 (FR-25, BR-P30 ~ BR-P34)."""

import dataclasses
import datetime as dt
import json

import pytest

from radar.analyze import Analyzer
from radar.hf_client import HFClient
from radar.news import (
    Article,
    FeedItem,
    analyze_news,
    extract_article,
    fallback_news,
    news_id,
    parse_feed,
)
from radar.publish import ServerClient
from radar.runner import EXIT_FAILED, EXIT_OK, Runner
from tests.conftest import KST_NOON, FakeHF, FakeServer, ScriptedProvider


def rss(*items) -> str:
    body = "".join(
        f'<item><title>{t}</title><pubDate>{d}</pubDate><link>{u}</link><guid isPermaLink="false">{u}</guid></item>'
        for t, d, u in items
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
        f"<channel><title>Hugging Face - Blog</title>{body}</channel></rss>"
    )


ARTICLE_HTML = """<!doctype html><html><head>
<meta property="og:image" content="https://cdn-uploads.huggingface.co/x.png">
<title>t</title><script>var x = "<p>no</p>";</script></head>
<body><header><nav><p>Models Datasets Spaces</p></nav></header>
<main><div class="blog-content prose">
<h1>llama.cpp v1</h1>
<p>llama.cpp makes it possible to run multi-modal LLMs across a wide range of hardware, from laptops to servers.</p>
<h2>Releases</h2><p>We now ship &amp; sign binaries.</p>
<ul><li>CUDA</li><li>Metal</li></ul>
<pre><code>cmake -B build
cmake --build build</code></pre>
<h2>Distribution</h2><p>Packages are on Homebrew.</p>
</div><aside><p>Upvote 12</p></aside></main>
<footer><p>© Hugging Face</p></footer></body></html>"""

FEED = rss(
    ("llama.cpp v1", "Fri, 13 Nov 2026 14:05:22 GMT", "https://huggingface.co/blog/ggml-org/llama-cpp-v1"),
    ("3D LoRA", "Thu, 12 Nov 2026 00:00:00 GMT", "https://huggingface.co/blog/3d-lora-finetuning"),
    ("Old post", "Fri, 26 Sep 2025 00:00:00 GMT", "https://huggingface.co/blog/old-post"),
    ("Elsewhere", "Fri, 13 Nov 2026 10:00:00 GMT", "https://example.com/blog/x"),
)


def test_news_id_only_for_hf_blog():
    assert news_id("https://huggingface.co/blog/ggml-org/llama-cpp-v1") == "ggml-org/llama-cpp-v1"
    assert news_id("https://huggingface.co/blog/3D-LoRA_finetuning") == "3d-lora_finetuning"
    assert news_id("https://example.com/blog/x") is None
    assert news_id("http://huggingface.co/blog/x") is None
    assert news_id("https://huggingface.co/papers/2611.1") is None
    assert news_id("https://huggingface.co/blog/a/b/c") is None


def test_parse_feed_reads_items_and_skips_foreign_links():
    items = parse_feed(FEED)
    assert [i.id for i in items] == ["ggml-org/llama-cpp-v1", "3d-lora-finetuning", "old-post"]
    assert items[0].published_at == dt.datetime(2026, 11, 13, 14, 5, 22, tzinfo=dt.UTC)
    assert items[0].raw["guid"] == "https://huggingface.co/blog/ggml-org/llama-cpp-v1"


def test_parse_feed_rejects_entities():
    with pytest.raises(ValueError):
        parse_feed('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><rss><channel></channel></rss>')


def test_extract_article_keeps_body_only():
    # BR-P31: blog-content 안의 본문, nav · aside · footer · script 제외
    article = extract_article(ARTICLE_HTML)
    assert article.content.startswith("## llama.cpp v1\nllama.cpp makes it possible")
    assert "We now ship & sign binaries." in article.content
    assert "- CUDA\n- Metal" in article.content
    assert "cmake -B build\ncmake --build build" in article.content
    for noise in ("Models Datasets", "Upvote", "© Hugging Face", "no</p>"):
        assert noise not in article.content
    assert article.headings == ["Releases", "Distribution"]
    assert article.image_url == "https://cdn-uploads.huggingface.co/x.png"


def test_extract_article_falls_back_to_body():
    html = "<html><body><div><p>" + "Plain article text. " * 5 + "</p></div></body></html>"
    assert extract_article(html).content.startswith("Plain article text.")


def test_fallback_news_without_ai():
    # BR-P32
    item = parse_feed(FEED)[0]
    news = fallback_news(item, extract_article(ARTICLE_HTML))
    assert news.summary.startswith("llama.cpp makes it possible")
    assert news.key_points == ["Releases", "Distribution"]
    assert news.summary_source == "abstract"
    assert news.organization == "ggml-org"
    assert news.source_raw["title"] == "llama.cpp v1"


def test_analyze_news_with_ai_and_fallback_on_bad_json():
    item = parse_feed(FEED)[0]
    article = extract_article(ARTICLE_HTML)
    good = json.dumps(
        {
            "topic": "training-optimization",
            "summary": "llama.cpp 1.0 출시",
            "key_points": ["a", "b"],
            "keywords": ["Inference", "inference", "GGUF"],
        }
    )
    provider = ScriptedProvider({"NEWS": [good]})
    news, fell_back = analyze_news(Analyzer(provider=provider), item, article)
    assert (news.summary, news.keywords, news.summary_source, fell_back) == (
        "llama.cpp 1.0 출시",
        ["inference", "gguf"],
        "ai",
        False,
    )
    assert "llama.cpp makes it possible" in provider.calls[0][1]
    bad = ScriptedProvider({"NEWS": ["not json", "still not"]})
    news, fell_back = analyze_news(Analyzer(provider=bad), item, article)
    assert (news.summary_source, fell_back) == ("abstract", True)
    assert len(bad.calls) == 2  # BR-P10: 1회 재요청


def test_news_payload_matches_server_contract(contract):
    # 계약: 서버 NewsIn 으로 검사
    schemas = contract
    news = fallback_news(parse_feed(FEED)[0], extract_article(ARTICLE_HTML))
    schemas.NewsIngest.model_validate({"provider": "none", "items": [json.loads(news.model_dump_json())]})
    empty = fallback_news(
        FeedItem("a/b", "https://huggingface.co/blog/a/b", "T", dt.datetime.now(dt.UTC), {}), Article()
    )
    schemas.NewsIngest.model_validate({"provider": "none", "items": [json.loads(empty.model_dump_json())]})


def make_runner(config, hf, server, provider=None):
    sleeps = []
    runner = Runner(
        config=config,
        hf=HFClient(hf.client(), sleep=lambda s: None),
        server=ServerClient(server.client(), token="secret-token-value", sleep=lambda s: None),
        analyzer=Analyzer(provider=provider),
        now=lambda: KST_NOON,
        sleep=sleeps.append,
    )
    return runner, sleeps


def news_config(config):
    import dataclasses

    return dataclasses.replace(config, collect=dataclasses.replace(config.collect, news=True))


def test_run_news_uploads_recent_new_posts_once(config):
    # BR-P30, BR-P31 (3초 간격), BR-P33
    config = news_config(config)
    pages = {"/blog/feed.xml": FEED, "/blog/ggml-org/llama-cpp-v1": ARTICLE_HTML}
    hf, server = FakeHF(pages=pages), FakeServer()
    runner, sleeps = make_runner(config, hf, server)
    assert runner.run_news(days=7) == EXIT_OK
    items = server.news[0]["items"]
    assert [i["id"] for i in items] == ["ggml-org/llama-cpp-v1", "3d-lora-finetuning"]
    assert items[0]["content"].startswith("## llama.cpp v1")
    assert items[1]["content"] == "" and items[1]["summary"] == "3D LoRA"  # 본문을 못 받아도 계속
    assert sleeps == [3.0, 3.0]
    # 두 번째 실행: 이미 올린 글은 다시 하지 않음
    assert runner.run_news(days=7) == EXIT_OK
    assert len(server.news) == 1
    record = json.loads((config.data_path / "runs.jsonl").read_text().splitlines()[-1])
    assert record["stage"] == "news" and record["news"] == 0


def test_run_news_reanalyzes_with_ai_after_none(config):
    config = news_config(config)
    hf, server = FakeHF(pages={"/blog/feed.xml": FEED}), FakeServer()
    runner, _ = make_runner(config, hf, server)
    runner.run_news(days=7)
    good = json.dumps({"topic": "other", "summary": "요약", "key_points": [], "keywords": []})
    ai_runner, _ = make_runner(config, hf, server, ScriptedProvider({"NEWS": lambda u: good}))
    assert ai_runner.run_news(days=7) == EXIT_OK
    assert server.news[-1]["provider"] == "fake"
    assert all(i["summary_source"] == "abstract" for i in server.news[-1]["items"])  # 본문이 없으면 규칙 결과


def test_run_news_in_batches_of_ten(config):
    config = news_config(config)
    posts = [(f"Post {i}", "Fri, 13 Nov 2026 10:00:00 GMT", f"https://huggingface.co/blog/p{i}") for i in range(23)]
    hf, server = FakeHF(pages={"/blog/feed.xml": rss(*posts)}), FakeServer()
    runner, _ = make_runner(config, hf, server)
    assert runner.run_news(days=7) == EXIT_OK
    assert [len(b["items"]) for b in server.news] == [10, 10, 3]
    assert runner.run_news(days=3) == EXIT_OK  # 기간 밖 (3일 전보다 오래됨)
    assert len(server.news) == 3


def test_upload_failure_keeps_posts_for_next_run(config):
    # BR-P33
    config = news_config(config)
    hf, server = FakeHF(pages={"/blog/feed.xml": FEED}), FakeServer(statuses=[500, 500, 500, 500])
    runner, _ = make_runner(config, hf, server)
    assert runner.run_news(days=7) == EXIT_FAILED
    assert not (config.data_path / "news_seen.json").exists()
    assert runner.run_news(days=7) == EXIT_OK
    assert len(server.news[-1]["items"]) == 2


def test_feed_failure_does_not_fail_daily(config):
    # BR-P34: 뉴스 실패는 일일 결과에 영향 없음, 실행 기록에 남김
    config = news_config(config)
    hf, server = FakeHF(days={"2026-11-16": []}), FakeServer()
    runner, _ = make_runner(config, hf, server)
    assert runner.run_daily() == EXIT_OK
    lines = [json.loads(x) for x in (config.data_path / "runs.jsonl").read_text().splitlines()]
    news = [x for x in lines if x["stage"] == "news"]
    assert news and news[0]["status"] == "failed"
    assert lines[-1]["status"] == "ok"  # 뉴스가 먼저 실패해도 논문은 그대로 처리


def test_news_disabled_does_nothing(config):
    hf, server = FakeHF(pages={"/blog/feed.xml": FEED}), FakeServer()
    runner, _ = make_runner(config, hf, server)
    assert runner.run_news(days=7) == EXIT_OK
    assert server.news == [] and hf.calls == []


def test_daily_uploads_news_before_papers(config):
    # 2026-11-18 사용자 요청 "뉴스먼저 나오게 해주면 안될까": 매일 실행은 뉴스 → 논문
    from tests.conftest import hf_item

    config = news_config(config)
    config = dataclasses.replace(config, collect=dataclasses.replace(config.collect, news_days=7))
    pages = {"/blog/feed.xml": FEED, "/blog/ggml-org/llama-cpp-v1": ARTICLE_HTML}
    hf = FakeHF(days={"2026-11-16": [hf_item("2611.00001")]}, pages=pages)
    server = FakeServer()
    runner, _ = make_runner(config, hf, server)
    assert runner.run_daily(backfill=False) == EXIT_OK
    assert [e[0] for e in server.events] == ["news", "daily"]
