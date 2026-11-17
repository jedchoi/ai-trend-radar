import dataclasses
import datetime as dt
import json

from radar.analyze import Analyzer
from radar.config import AIConfig
from radar.hf_client import HFClient
from radar.publish import ServerClient
from radar.runner import EXIT_CONFIG, EXIT_FAILED, EXIT_OK, Runner, plan_dates
from tests.conftest import KST_NOON, FakeHF, FakeServer, ScriptedProvider, hf_item

D = dt.date


def build(config, hf: FakeHF, server: FakeServer, provider=None, now=KST_NOON, max_ai=60):
    return Runner(
        config=config,
        hf=HFClient(hf.client(), sleep=lambda s: None),
        server=ServerClient(server.client(), token="secret-token-value", sleep=lambda s: None),
        analyzer=Analyzer(provider=provider, max_ai_papers=max_ai),
        now=lambda: now,
    )


def trending():
    return {
        "models": [{"id": "a/m1", "likes": 1, "trendingScore": 9}, {"id": "a/m2", "likes": 1, "trendingScore": 5}],
        "datasets": [{"id": "a/d1", "likes": 1}],
        "spaces": [{"id": "a/s1", "likes": 1}],
    }


def read_runs(config):
    path = config.data_path / "runs.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_plan_dates_rules():
    # BR-P14
    target = D(2026, 11, 16)
    assert plan_dates(None, target, None) == [target]
    assert plan_dates(D(2026, 11, 13), target, None) == [D(2026, 11, 14), D(2026, 11, 15), D(2026, 11, 16)]
    assert plan_dates(D(2026, 11, 16), target, None) == []
    assert plan_dates(D(2026, 10, 1), target, None) == [D(2026, 11, 10) + dt.timedelta(days=i) for i in range(7)]
    assert plan_dates(D(2026, 11, 13), target, D(2026, 11, 1)) == [D(2026, 11, 1)]


def test_daily_none_end_to_end(config):
    # AC-16-1, AC-17-1: 수집 → 선별 → 분석 → 업로드, 키 없이
    hf = FakeHF(
        days={
            "2026-11-16": [
                hf_item("2611.00001", upvotes=5),
                hf_item("2611.00002", upvotes=50, title="Web agents that use tools"),
                hf_item("2611.00003", upvotes=1),
            ]
        },
        trending=trending(),
    )
    server = FakeServer()
    code = build(config, hf, server).run_daily()
    assert code == EXIT_OK
    assert len(server.uploads) == 1
    body = server.uploads[0]
    assert body["date"] == "2026-11-16"  # BR-P01: 한국 시간 어제
    assert body["provider"] == "none"
    assert {p["id"] for p in body["papers"] if p["featured"]} == {"2611.00002", "2611.00001"}
    assert [h["id"] for h in body["hub"]] == ["a/m1", "a/m2", "a/d1", "a/s1"]
    assert body["papers"][1]["topic"] == "agents"
    assert server.auth[0] == "Bearer secret-token-value"
    state = json.loads((config.data_path / "state.json").read_text())
    assert state == {"last_success_date": "2026-11-16"}
    assert (config.data_path / "raw" / "2026-11-16.json").exists()


def test_run_record_line(config):
    # AC-16-2, BR-P16: 기록 필드, 비밀 없음
    hf = FakeHF(days={"2026-11-16": [hf_item("2611.00001")]}, trending=trending())
    build(config, hf, FakeServer()).run_daily()
    record = read_runs(config)[-1]
    assert {k: record[k] for k in ("date", "status", "stage", "papers", "featured", "provider", "ai_fallbacks")} == {
        "date": "2026-11-16",
        "status": "ok",
        "stage": "done",
        "papers": 1,
        "featured": 1,
        "provider": "none",
        "ai_fallbacks": 0,
    }
    assert "duration_s" in record and "ts" in record
    assert "secret-token-value" not in (config.data_path / "runs.jsonl").read_text()


def test_zero_paper_day_uploads_hub_only(config):
    # AC-16-3, BR-P15
    hf = FakeHF(days={}, trending=trending())
    server = FakeServer()
    assert build(config, hf, server).run_daily() == EXIT_OK
    assert server.uploads[0]["papers"] == [] and server.uploads[0]["headline"] == []
    assert len(server.uploads[0]["hub"]) == 4


def test_backfill_processes_missing_days_in_order(config):
    # AC-18-1
    config.data_path.mkdir(parents=True)
    (config.data_path / "state.json").write_text(json.dumps({"last_success_date": "2026-11-13"}))
    hf = FakeHF(days={}, trending=trending())
    server = FakeServer()
    assert build(config, hf, server).run_daily() == EXIT_OK
    assert [u["date"] for u in server.uploads] == ["2026-11-14", "2026-11-15", "2026-11-16"]


def test_explicit_date_only(config):
    # AC-18-2: --date 는 그 날짜만, 상태는 더 늦은 날짜만 갱신
    config.data_path.mkdir(parents=True)
    (config.data_path / "state.json").write_text(json.dumps({"last_success_date": "2026-11-13"}))
    server = FakeServer()
    assert build(config, FakeHF(trending=trending()), server).run_daily(explicit=D(2026, 11, 1)) == EXIT_OK
    assert [u["date"] for u in server.uploads] == ["2026-11-01"]
    assert json.loads((config.data_path / "state.json").read_text())["last_success_date"] == "2026-11-13"


def test_no_backfill_flag(config):
    config.data_path.mkdir(parents=True)
    (config.data_path / "state.json").write_text(json.dumps({"last_success_date": "2026-11-10"}))
    server = FakeServer()
    build(config, FakeHF(trending=trending()), server).run_daily(backfill=False)
    assert [u["date"] for u in server.uploads] == ["2026-11-16"]


def test_upload_auth_failure_stops_and_records(config):
    # AC-19-1, BR-P12, BR-P18: 401 은 재시도 없이 실패, 다음 날짜 진행 안 함, 상태 갱신 안 함
    config.data_path.mkdir(parents=True)
    (config.data_path / "state.json").write_text(json.dumps({"last_success_date": "2026-11-14"}))
    server = FakeServer(statuses=[401])
    code = build(config, FakeHF(trending=trending()), server).run_daily()
    assert code == EXIT_FAILED
    assert len(server.auth) == 1
    record = read_runs(config)[-1]
    assert (record["date"], record["status"], record["stage"]) == ("2026-11-15", "failed", "upload")
    assert json.loads((config.data_path / "state.json").read_text())["last_success_date"] == "2026-11-14"


def test_upload_server_error_is_retried(config):
    # BR-P12: 5xx 는 3회 시도
    server = FakeServer(statuses=[502, 503, 200])
    assert build(config, FakeHF(trending=trending()), server).run_daily() == EXIT_OK
    assert len(server.auth) == 3


def test_collect_failure_is_recorded(config):
    # BR-P18
    hf = FakeHF(fail={"/api/daily_papers": [500, 500, 500]}, trending=trending())
    server = FakeServer()
    assert build(config, hf, server).run_daily() == EXIT_FAILED
    assert server.uploads == []
    assert read_runs(config)[-1]["stage"] == "collect"


def test_config_problems_exit_before_collecting(config):
    # AC-17-3, BR-P11
    bad = dataclasses.replace(config, ai=AIConfig(provider="anthropic", model="m", api_key_env="NO_SUCH_KEY"))
    hf = FakeHF(trending=trending())
    runner = build(bad, hf, FakeServer())
    assert runner.run_daily() == EXIT_CONFIG
    assert hf.calls == []


def test_dry_run_writes_payload(config, tmp_path):
    out = tmp_path / "payload.json"
    server = FakeServer()
    hf = FakeHF(days={"2026-11-16": [hf_item("2611.00001")]}, trending=trending())
    assert build(config, hf, server).run_daily(dry_run_out=out) == EXIT_OK
    assert server.uploads == []
    assert json.loads(out.read_text())[0]["date"] == "2026-11-16"
    assert not (config.data_path / "state.json").exists()


def test_reports_on_monday_and_first_of_month(config):
    # AC-20-1, BR-P17: 월요일 → 지난주, 1일 → 지난달
    stats = {"key": "2026-W46", "paper_count": 3, "topics": [{"topic": "agents", "count": 3}], "rising_keywords": []}
    server = FakeServer(stats={"2026-W46": stats, "2026-10": {**stats, "key": "2026-10"}})
    monday = dt.datetime(2026, 11, 16, 0, 0, tzinfo=dt.UTC)  # KST 11-16 (월) 09:00
    build(config, FakeHF(), server, now=monday).run_reports()
    assert [(r["period"], r["key"]) for r in server.reports] == [("week", "2026-W46")]
    assert "에이전트" in server.reports[0]["narrative"]
    first = dt.datetime(2026, 11, 1, 0, 0, tzinfo=dt.UTC)  # KST 11-01 (일)
    build(config, FakeHF(), server, now=first).run_reports()
    assert server.reports[-1]["period"] == "month" and server.reports[-1]["key"] == "2026-10"


def test_reports_skip_when_no_stats_or_not_due(config):
    server = FakeServer()
    monday = dt.datetime(2026, 11, 16, 0, 0, tzinfo=dt.UTC)
    build(config, FakeHF(), server, now=monday).run_reports()
    build(config, FakeHF(), server).run_reports()  # 화요일
    assert server.reports == []


def test_reports_use_ai_narrative(config):
    # AC-20-1: AI 해석 문장
    stats = {"key": "2026-W46", "paper_count": 3, "topics": [], "rising_keywords": []}
    server = FakeServer(stats={"2026-W46": stats})
    provider = ScriptedProvider({"REPORT": [json.dumps({"narrative": "AI 해석"})]})
    monday = dt.datetime(2026, 11, 16, 0, 0, tzinfo=dt.UTC)
    build(config, FakeHF(), server, provider=provider, now=monday).run_reports()
    assert server.reports[0] == {"period": "week", "key": "2026-W46", "narrative": "AI 해석", "provider": "fake"}


def test_ai_fallback_count_recorded(config):
    def boom(user):
        raise RuntimeError("x")

    provider = ScriptedProvider({"BRIEF": boom, "DETAIL": boom, "HEADLINE": boom})
    hf = FakeHF(days={"2026-11-16": [hf_item("2611.00001")]}, trending=trending())
    build(config, hf, FakeServer(), provider=provider).run_daily()
    assert read_runs(config)[-1]["ai_fallbacks"] == 3
