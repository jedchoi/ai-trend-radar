import hashlib
import json
from pathlib import Path

import pytest

from radar import cli
from radar.config import check_server_config, load_config, read_token

EXAMPLE = Path(__file__).resolve().parents[1] / "deploy" / "config.example.toml"


def test_example_config_loads():
    cfg = load_config(EXAMPLE)
    assert cfg.ai.provider == "none"
    assert cfg.collect.models == 10 and cfg.select.max_featured == 5
    assert cfg.data_path.is_absolute()


def test_load_config_overrides(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text(
        '[server]\nurl = "https://x.example"\n[ai]\nprovider = "cli"\ncommand = ["claude", "-p"]\n'
        f'[paths]\ndata_dir = "{tmp_path / "d"}"\n'
    )
    cfg = load_config(path)
    assert cfg.server.url == "https://x.example"
    assert cfg.ai.command == ["claude", "-p"]
    assert cfg.data_path == tmp_path / "d"


def test_unknown_section_or_key_is_an_error(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text('[ai]\nprovder = "x"\n')
    with pytest.raises(ValueError, match="provder"):
        load_config(path)


def test_server_url_must_be_https(config):
    # NFR-P07
    import dataclasses

    from radar.config import ServerConfig

    for url, ok in [
        ("https://a.example", True),
        ("http://a.example", False),
        ("http://localhost:8000", True),
        ("http://127.0.0.1:8000", True),
        ("", False),
    ]:
        cfg = dataclasses.replace(config, server=ServerConfig(url=url, token_env="RADAR_TEST_TOKEN"))
        assert (check_server_config(cfg.server, {"RADAR_TEST_TOKEN": "t"}) == []) is ok, url


def test_token_from_env_or_file(tmp_path):
    from radar.config import ServerConfig

    assert read_token(ServerConfig(url="https://a", token_env="T"), {"T": " abc \n"}) == "abc"
    token_file = tmp_path / "token"
    token_file.write_text("filetoken\n")
    token_file.chmod(0o600)
    assert read_token(ServerConfig(url="https://a", token_env="T", token_file=str(token_file)), {}) == "filetoken"
    assert read_token(ServerConfig(url="https://a", token_env="T"), {}) is None


def test_missing_token_is_reported():
    from radar.config import ServerConfig

    problems = check_server_config(ServerConfig(url="https://a", token_env="T"), {})
    assert any("T" in p for p in problems)


def test_cli_token_prints_token_and_hash(capsys):
    assert cli.main(["token"]) == 0
    out = capsys.readouterr().out
    token = out.split("RADAR_INGEST_TOKEN=", 1)[1].split()[0]
    assert len(token) >= 43
    assert hashlib.sha256(token.encode()).hexdigest() in out


def test_cli_check_reports_problems(tmp_path, capsys):
    path = tmp_path / "c.toml"
    path.write_text(
        '[server]\nurl = "http://insecure.example"\ntoken_env = "NOPE_TOKEN"\n'
        '[ai]\nprovider = "anthropic"\nmodel = "m"\napi_key_env = "NOPE_KEY"\n'
    )
    assert cli.main(["--config", str(path), "check", "--offline"]) == 3
    out = capsys.readouterr().out
    assert "NOPE_TOKEN" in out and "NOPE_KEY" in out and "https" in out


def test_cli_check_ok(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OK_TOKEN", "t")
    path = tmp_path / "c.toml"
    path.write_text('[server]\nurl = "https://a.example"\ntoken_env = "OK_TOKEN"\n')
    assert cli.main(["--config", str(path), "check", "--offline"]) == 0
    assert "문제 없음" in capsys.readouterr().out


def test_cli_daily_dry_run_wires_components(tmp_path, monkeypatch):
    # cli 가 설정대로 부품을 만들어 Runner 를 부르는지 (네트워크는 Runner 대역으로 막음)
    seen = {}

    class FakeRunner:
        def __init__(self, **kw):
            seen.update(kw)

        def run_daily(self, explicit=None, backfill=True, dry_run_out=None):
            seen["args"] = (explicit, backfill, dry_run_out)
            return 0

        def run_reports(self):
            seen["reports"] = True

    monkeypatch.setattr(cli, "Runner", FakeRunner)
    monkeypatch.setenv("OK_TOKEN", "t")
    path = tmp_path / "c.toml"
    path.write_text(f'[server]\nurl = "https://a.example"\ntoken_env = "OK_TOKEN"\n[paths]\ndata_dir = "{tmp_path}"\n')
    out = tmp_path / "o.json"
    assert (
        cli.main(["--config", str(path), "daily", "--date", "2026-11-01", "--no-backfill", "--dry-run", str(out)]) == 0
    )
    assert seen["args"][0].isoformat() == "2026-11-01" and seen["args"][1] is False
    assert "reports" not in seen  # dry-run 은 리포트 안 올림
    assert cli.main(["--config", str(path), "report"]) == 0
    assert seen["reports"] is True


def test_cli_daily_bad_date(capsys):
    with pytest.raises(SystemExit):
        cli.main(["daily", "--date", "2026-13-01"])


def test_prompts_are_plain_files():
    # NFR-P01: 프롬프트는 제공자와 무관한 파일, 첫 줄이 작업 이름
    prompts = Path(__file__).resolve().parents[1] / "radar" / "prompts"
    names = {p.stem: p.read_text("utf-8").splitlines()[0] for p in prompts.glob("*.md")}
    assert names == {
        "brief": "BRIEF",
        "detail": "DETAIL",
        "headline": "HEADLINE",
        "report": "REPORT",
        "news": "NEWS",
        "translate": "TRANSLATE",
    }
    assert json.dumps(names)


def test_cli_backfill_wiring_and_limits(tmp_path, monkeypatch):
    # BR-P19: radar backfill --days N (1~120)
    seen = {}

    class FakeRunner:
        def __init__(self, **kw):
            pass

        def run_backfill(self, days, until, reports):
            seen.update(days=days, until=until, reports=reports)
            return 0

    monkeypatch.setattr(cli, "Runner", FakeRunner)
    monkeypatch.setenv("OK_TOKEN", "t")
    path = tmp_path / "c.toml"
    path.write_text(f'[server]\nurl = "https://a.example"\ntoken_env = "OK_TOKEN"\n[paths]\ndata_dir = "{tmp_path}"\n')
    assert cli.main(["--config", str(path), "backfill"]) == 0
    assert seen == {"days": 90, "until": None, "reports": True}
    assert cli.main(["--config", str(path), "backfill", "--days", "30", "--until", "2026-11-01", "--no-reports"]) == 0
    assert seen["days"] == 30 and seen["until"].isoformat() == "2026-11-01" and seen["reports"] is False
    for bad in ("0", "121", "x"):
        with pytest.raises(SystemExit):
            cli.main(["--config", str(path), "backfill", "--days", bad])


def test_cli_translate_and_daily_order(tmp_path, monkeypatch):
    # BR-P45: radar translate --days N --max-minutes M, daily 은 논문 → 리포트 → 번역
    seen = []

    class FakeRunner:
        def __init__(self, **kw):
            pass

        def config_problems(self, upload=True):
            return []

        def run_daily(self, explicit=None, backfill=True, dry_run_out=None):
            seen.append("daily")
            return 0

        def run_reports(self):
            seen.append("reports")

        def run_translate(self, days=None, max_minutes=None):
            seen.append(("translate", days, max_minutes))
            return 0

    monkeypatch.setattr(cli, "Runner", FakeRunner)
    monkeypatch.setenv("OK_TOKEN", "t")
    path = tmp_path / "c.toml"
    path.write_text(
        f'[server]\nurl = "https://a.example"\ntoken_env = "OK_TOKEN"\n[paths]\ndata_dir = "{tmp_path}"\n'
        "[translate]\ndays = 30\nmax_minutes = 60\n"
    )
    assert cli.main(["--config", str(path), "translate", "--days", "90", "--max-minutes", "0"]) == 0
    assert cli.main(["--config", str(path), "daily"]) == 0
    assert seen == [("translate", 90, 0), "daily", "reports", ("translate", None, None)]
    assert cli.load_config(path).translate.days == 30
