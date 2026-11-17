"""계약 테스트: 파이프라인 업로드가 서버 `DigestIngest` 를 통과하는지 서버 스키마로 직접 검사."""

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from radar.analyze import Analyzer
from radar.models import HubItem, RawPaper, Topic

SCHEMAS = Path(__file__).resolve().parents[2] / "server" / "app" / "schemas.py"


@pytest.fixture(scope="module")
def server_schemas():
    if not SCHEMAS.exists():
        pytest.skip("server/ 없음")
    spec = importlib.util.spec_from_file_location("server_schemas", SCHEMAS)
    module = importlib.util.module_from_spec(spec)
    sys.modules["server_schemas"] = module  # pydantic 이 지연 주석을 풀 수 있게 등록
    spec.loader.exec_module(module)
    return module


def test_payload_passes_server_contract(server_schemas):
    raws = [
        RawPaper(
            id="2611.15777",
            title="SO-Arena",
            authors=["A"],
            abstract="We benchmark.",
            upvotes=85,
            ai_summary="Benchmark of fast models.",
            ai_keywords=["System One", "Benchmark"],
            github_url="https://github.com/holdrain/SO-Arena",
            github_stars=3,
            published_at=dt.date(2026, 11, 11),
        ),
        RawPaper(id="2611.00002", title="Other", ai_summary=None, abstract=""),
    ]
    hub = [
        HubItem(
            kind="model",
            rank=1,
            id="Qwen/Qwen3.8-Flash-Next",
            likes=4502,
            downloads=158598,
            trending_score=4286.0,
            task="image-text-to-text",
        )
    ]
    payload, _ = Analyzer(provider=None, max_ai_papers=60).analyze_day(
        dt.date(2026, 11, 13),
        raws,
        {"2611.15777": Topic.EVALUATION_BENCHMARK, "2611.00002": Topic.OTHER},
        ["2611.15777"],
        hub,
    )
    body = json.loads(payload.model_dump_json())
    server_schemas.DigestIngest.model_validate(body)


def test_topics_match_server(server_schemas):
    assert [t.value for t in Topic] == [t.value for t in server_schemas.Topic]
