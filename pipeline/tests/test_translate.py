"""번역 (FR-34 ~ FR-36, BR-P40 ~ BR-P45)."""

import dataclasses
import datetime as dt
import json

from radar.analyze import Analyzer
from radar.config import TranslateConfig
from radar.hf_client import HFClient
from radar.publish import ServerClient
from radar.runner import EXIT_OK, Runner
from radar.translate import Job, Translator, same_shape, split_text
from tests.conftest import KST_NOON, FakeHF, FakeServer, ScriptedProvider

DETAIL = {"what": "무엇", "novelty": "새로움", "why": "중요", "apply": "적용"}


def paper(pid, featured=False, full=False):
    return {
        "id": pid,
        "title": f"Paper {pid}",
        "abstract": f"Abstract of {pid}.",
        "one_liner": f"{pid} 요약",
        "featured": featured,
        "detail": DETAIL if featured else None,
        "glossary": [{"term": "용어", "explanation": "설명"}] if featured else [],
        "has_full_text": full,
    }


def server_pages(papers=None, headline=None, news_content="Body one.\n\nBody two."):
    papers = (
        papers
        if papers is not None
        else [paper("2611.00001", True, True)] + [paper(f"2611.0000{i}") for i in range(2, 7)]
    )
    return {
        "/api/v1/digests": {"items": [{"date": "2026-11-16"}, {"date": "2026-09-01"}]},
        "/api/v1/digests/2026-11-16": {
            "date": "2026-11-16",
            "headline": headline or ["첫째", "둘째"],
            "papers": papers,
        },
        "/api/v1/news": {
            "items": [{"id": "a/post", "title": "Post", "summary": "요약", "published_at": "2026-11-15T10:00:00Z"}],
            "total": 1,
        },
        "/api/v1/news/a/post": {
            "id": "a/post",
            "title": "Post",
            "summary": "요약",
            "key_points": ["핵심"],
            "content": news_content,
        },
        "/api/v1/trends/periods": {"weeks": ["2026-W47"], "months": []},
        "/api/v1/trends/weekly/2026-W47": {"narrative": "이번 주"},
        "/api/v1/papers/2611.00001": {"paper": {"full_text": "# Intro\n\nLong body."}},
    }


def mark(value):
    if isinstance(value, dict):
        return {k: mark(v) for k, v in value.items()}
    if isinstance(value, list):
        return [mark(v) for v in value]
    return f"T:{value}" if isinstance(value, str) else value


def good_ai():
    return ScriptedProvider(
        {
            "TRANSLATE": lambda u: json.dumps(mark(json.loads(u[u.index("{") :])), ensure_ascii=False),
            "TRANSLATE_TEXT": lambda u: "번역 " + u.split("\n", 1)[0][:2000] + " 끝" * 20,
        }
    )


def make(config, server, provider, minutes=0, clock=None):
    config = dataclasses.replace(config, translate=TranslateConfig(enabled=True, max_minutes=minutes, chunk_chars=50))
    analyzer = Analyzer(provider=provider)
    runner = Runner(
        config=config,
        hf=HFClient(FakeHF().client(), sleep=lambda s: None),
        server=ServerClient(server.client(), token="t", sleep=lambda s: None),
        analyzer=analyzer,
        now=lambda: KST_NOON,
        sleep=lambda s: None,
    )
    return runner


def uploaded(server):
    return [item for batch in server.translations for item in batch["items"]]


def test_translates_short_first_then_long_and_uploads(config):
    # BR-P40, BR-P41, FR-34
    server = FakeServer(pages=server_pages())
    provider = good_ai()
    assert make(config, server, provider).run_translate(days=30) == EXIT_OK
    items = uploaded(server)
    keys = [(i["kind"], i["key"], i["lang"], tuple(sorted(i["fields"]))) for i in items]
    assert ("digest", "2026-11-16", "en", ("headline",)) in keys
    assert ("paper", "2611.00001", "ko", ("title",)) in keys  # 논문 원문 (초록 · 본문) 은 영어 그대로 (FR-34 개정)
    assert ("paper", "2611.00001", "en", ("detail", "glossary", "one_liner")) in keys
    assert ("paper", "2611.00002", "en", ("one_liner",)) in keys
    assert ("news", "a/post", "ko", ("title",)) in keys
    assert ("news", "a/post", "en", ("key_points", "summary")) in keys
    assert ("report", "week:2026-W47", "en", ("narrative",)) in keys
    long = [k for k in keys if k[3] in (("content",), ("full_text",))]
    assert long == [("news", "a/post", "ko", ("content",))]
    assert all("abstract" not in i["fields"] and "full_text" not in i["fields"] for i in items)
    assert keys.index(long[0]) > max(i for i, k in enumerate(keys) if k[3] not in (("content",), ("full_text",)))
    kinds = [c[0] for c in provider.calls]
    # 묶음: 논문 제목 (ko) 6편 → 1번 (10편씩), 요약 (en) 6편 → 2번 (5편씩),
    # 뉴스 제목 1번, 세 줄 · 뉴스 en · 리포트 각 1번
    assert kinds.count("TRANSLATE") == 1 + 2 + 1 + 3
    assert kinds.count("TRANSLATE_TEXT") >= 1
    assert all("Long body" not in u for _, u in provider.calls)  # 논문 본문은 번역 요청하지 않음
    assert next(i for i in items if i["kind"] == "paper" and i["lang"] == "en")["fields"]["detail"]["what"] == "T:무엇"
    # 2026-09-01 은 기간 (30일) 밖
    assert all(i["key"] != "2026-09-01" for i in items)


def test_translations_match_server_contract(config, contract):
    server = FakeServer(pages=server_pages())
    make(config, server, good_ai()).run_translate(days=30)
    for batch in server.translations:
        contract.TranslationIngest.model_validate(batch)


def test_second_run_skips_done_and_retranslates_changed(config):
    # BR-P43
    server = FakeServer(pages=server_pages())
    make(config, server, good_ai()).run_translate(days=30)
    first = len(uploaded(server))
    provider = good_ai()
    make(config, server, provider).run_translate(days=30)
    assert provider.calls == [] and len(uploaded(server)) == first
    # AI 재분석으로 한 줄 요약이 바뀐 논문만 다시
    changed = server_pages()
    changed["/api/v1/digests/2026-11-16"]["papers"][1]["one_liner"] = "새 요약"
    server.pages = changed
    provider = good_ai()
    make(config, server, provider).run_translate(days=30)
    again = uploaded(server)[first:]
    assert [(i["key"], i["lang"]) for i in again] == [("2611.00002", "en")]


def test_bad_output_is_retried_then_skipped(config):
    # BR-P42: 형식이 틀리면 1회 재요청, 그래도 틀리면 그 항목만 건너뜀 (다음 실행에서 다시)
    calls = []

    def flaky(u):
        calls.append(u)
        data = json.loads(u[u.index("{") :])
        if "narrative" in data:
            return "not json"
        return json.dumps(mark(data), ensure_ascii=False)

    provider = ScriptedProvider({"TRANSLATE": flaky, "TRANSLATE_TEXT": lambda u: ""})
    server = FakeServer(pages=server_pages())
    runner = make(config, server, provider)
    assert runner.run_translate(days=30) == EXIT_OK
    kinds = {i["kind"] for i in uploaded(server)}
    assert "report" not in kinds and "paper" in kinds
    assert all(i["fields"].keys() - {"content", "full_text"} for i in uploaded(server))  # 긴 본문 실패 → 없음
    record = json.loads((runner.data / "runs.jsonl").read_text().splitlines()[-1])
    assert record["stage"] == "translate" and record["failed"] >= 2  # 리포트 · 뉴스 본문
    state = json.loads((runner.data / "translated.json").read_text())
    assert "report:week:2026-W47:en:short" not in state


def test_batch_asks_again_for_missing_ids(config):
    asked = []

    def partial(u):
        data = json.loads(u[u.index("{") :])
        asked.append(sorted(data))
        if len(data) > 1:
            first = sorted(data)[0]
            return json.dumps({first: mark(data[first])}, ensure_ascii=False)
        return json.dumps(mark(data), ensure_ascii=False)

    translator = Translator(ScriptedProvider({"TRANSLATE": partial}), None, None)
    got = translator.translate_batch("ko", {"a": {"title": "A"}, "b": {"title": "B"}})
    assert got == {"a": {"title": "T:A"}, "b": {"title": "T:B"}}
    assert asked == [["a", "b"], ["b"]]


def test_long_text_split_and_joined_in_order():
    text = "\n\n".join(f"Paragraph {i} " + "x" * 30 for i in range(5))
    chunks = split_text(text, 80)
    assert all(len(c) <= 80 for c in chunks) and "\n\n".join(chunks) == text
    huge = "word " * 100
    assert all(len(c) <= 50 for c in split_text(huge, 50))
    assert "".join(split_text("a" * 120, 50)) == "a" * 120
    translator = Translator(
        ScriptedProvider({"TRANSLATE_TEXT": lambda u: "번역:" + u.strip()}), None, None, chunk_chars=80
    )
    out = translator.translate_text("ko", text)
    assert out.count("번역:") == len(chunks) and out.index("Paragraph 0") < out.index("Paragraph 4")


def test_too_short_translation_fails_whole_text():
    translator = Translator(ScriptedProvider({"TRANSLATE_TEXT": lambda u: "짧"}), None, None, chunk_chars=50)
    assert translator.translate_text("ko", "a long paragraph " * 10) is None


def test_time_limit_stops_and_keeps_progress(config):
    # BR-P44
    ticks = iter(range(0, 10_000, 30))  # 호출마다 30초
    server = FakeServer(pages=server_pages())
    config = dataclasses.replace(config, translate=TranslateConfig(enabled=True, max_minutes=1, chunk_chars=50))
    translator = Translator(
        good_ai(),
        ServerClient(server.client(), token="t", sleep=lambda s: None),
        config.data_path / "t.json",
        chunk_chars=50,
        max_minutes=1,
        clock=lambda: next(ticks),
    )
    result = translator.run(30, dt.date(2026, 11, 17))
    assert result["stopped"] is True
    assert 0 < result["done"] < 13
    state = json.loads((config.data_path / "t.json").read_text())
    assert len(state) == result["done"]


def test_no_ai_skips_translation(config):
    server = FakeServer(pages=server_pages())
    assert make(config, server, None).run_translate(days=30) == EXIT_OK
    assert server.translations == []


def test_same_shape_rules():
    assert same_shape({"a": ["x", {"b": "y"}]}, {"a": ["X", {"b": "Y"}]})
    assert not same_shape({"a": "x"}, {"a": ""})
    assert not same_shape({"a": "x"}, {"b": "x"})
    assert not same_shape(["x", "y"], ["x"])
    assert Job("paper", "1", "ko", "short", {"a": 1}).id == "paper:1:ko:short"
