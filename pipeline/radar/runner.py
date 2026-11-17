"""실행 (C-P8): 하루 처리, 빠진 날 채우기, 리포트, 상태 · 실행 기록."""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from zoneinfo import ZoneInfo

from radar.analyze import Analyzer
from radar.config import Config, check_server_config
from radar.hf_client import HFClient
from radar.models import DigestPayload, Topic
from radar.providers import check_ai_config
from radar.publish import ServerClient
from radar.select import select_featured
from radar.topics import classify

KST = ZoneInfo("Asia/Seoul")
BACKFILL_DAYS = 7
EXIT_OK, EXIT_FAILED, EXIT_CONFIG = 0, 2, 3


def plan_dates(
    last: dt.date | None, target: dt.date, explicit: dt.date | None, max_days: int = BACKFILL_DAYS
) -> list[dt.date]:
    """BR-P14."""
    if explicit is not None:
        return [explicit]
    if last is None:
        return [target]
    start = max(last + dt.timedelta(days=1), target - dt.timedelta(days=max_days - 1))
    return [start + dt.timedelta(days=i) for i in range((target - start).days + 1)]


class StepFailed(Exception):
    def __init__(self, stage: str, error: Exception):
        super().__init__(f"{stage}: {error}")
        self.stage = stage
        self.error = error


class Runner:
    def __init__(
        self,
        config: Config,
        hf: HFClient,
        server: ServerClient,
        analyzer: Analyzer,
        now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC),
        env=None,
    ) -> None:
        self.config = config
        self.hf = hf
        self.server = server
        self.analyzer = analyzer
        self.now = now
        self.env = os.environ if env is None else env
        self.data = config.data_path

    # ---------- 상태 · 기록 ----------

    def today_kst(self) -> dt.date:
        return self.now().astimezone(KST).date()

    def _state_path(self) -> Path:
        return self.data / "state.json"

    def last_success(self) -> dt.date | None:
        try:
            value = json.loads(self._state_path().read_text())["last_success_date"]
            return dt.date.fromisoformat(value)
        except (FileNotFoundError, KeyError, ValueError):
            return None

    def _mark_success(self, day: dt.date) -> None:
        last = self.last_success()
        if last is None or day > last:
            self.data.mkdir(parents=True, exist_ok=True)
            self._state_path().write_text(json.dumps({"last_success_date": day.isoformat()}))

    def _record(self, **fields) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        line = {"ts": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), **fields}
        with (self.data / "runs.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    def config_problems(self, upload: bool = True) -> list[str]:
        """BR-P11. 업로드하지 않는 실행 (--dry-run) 은 서버 주소 · 토큰을 요구하지 않는다."""
        problems = check_ai_config(self.config.ai, self.env)
        if upload:
            problems += check_server_config(self.config.server, self.env)
        return problems

    # ---------- 하루 처리 ----------

    def process_day(self, day: dt.date) -> tuple[DigestPayload, int]:
        stage = "collect"
        try:
            raws = self.hf.daily_papers(day)
            c = self.config.collect
            hub = (
                self.hf.trending("model", c.models)
                + self.hf.trending("dataset", c.datasets)
                + self.hf.trending("space", c.spaces)
            )
            raw_dir = self.data / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / f"{day.isoformat()}.json").write_text(
                json.dumps(
                    {"papers": [r.model_dump(mode="json") for r in raws], "hub": [h.model_dump() for h in hub]},
                    ensure_ascii=False,
                )
            )

            stage = "select"
            topics = {r.id: classify(r.title, r.ai_keywords, r.abstract) for r in raws}
            focus = {Topic(t) for t in self.config.select.focus_topics if t in Topic._value2member_map_}
            featured = select_featured(raws, topics, self.config.select.max_featured, focus)

            stage = "analyze"
            return self.analyzer.analyze_day(day, raws, topics, featured, hub)
        except Exception as exc:  # noqa: BLE001 - 단계 이름과 함께 기록하고 중단
            raise StepFailed(stage, exc) from exc

    def run_daily(self, explicit: dt.date | None = None, backfill: bool = True, dry_run_out: Path | None = None) -> int:
        problems = self.config_problems(upload=dry_run_out is None)
        if problems:
            for p in problems:
                print(f"설정 문제: {p}")
            return EXIT_CONFIG
        target = self.today_kst() - dt.timedelta(days=1)  # BR-P01
        last = self.last_success() if backfill else None
        days = plan_dates(last, target, explicit)
        dry_payloads = []
        for day in days:
            started = time.monotonic()
            base = {"date": day.isoformat(), "provider": self.analyzer.provider_name}
            try:
                payload, fallbacks = self.process_day(day)
                if dry_run_out is not None:
                    dry_payloads.append(json.loads(payload.model_dump_json()))
                else:
                    try:
                        self.server.upload_digest(payload)
                    except Exception as exc:  # noqa: BLE001
                        raise StepFailed("upload", exc) from exc
                    self._mark_success(day)
            except StepFailed as failed:
                self._record(
                    **base,
                    status="failed",
                    stage=failed.stage,
                    papers=0,
                    featured=0,
                    ai_fallbacks=0,
                    duration_s=round(time.monotonic() - started, 2),
                    error=str(failed.error)[:300],
                )
                print(f"{day} 실패 ({failed.stage}): {failed.error}")
                return EXIT_FAILED  # BR-P18: 다음 날짜로 넘어가지 않음
            self._record(
                **base,
                status="ok",
                stage="done",
                papers=len(payload.papers),
                featured=sum(p.featured for p in payload.papers),
                ai_fallbacks=fallbacks,
                duration_s=round(time.monotonic() - started, 2),
                error=None,
            )
            print(f"{day} 완료: 논문 {len(payload.papers)}편, AI 대체 {fallbacks}건")
        if dry_run_out is not None:
            Path(dry_run_out).write_text(json.dumps(dry_payloads, ensure_ascii=False, indent=2), "utf-8")
        if not days:
            print("처리할 날짜 없음 (이미 최신)")
        return EXIT_OK

    # ---------- 리포트 ----------

    def due_reports(self) -> list[tuple[str, str]]:
        """BR-P17: 월요일 → 지난 ISO 주, 1일 → 지난달."""
        today = self.today_kst()
        due = []
        if today.weekday() == 0:
            year, week, _ = (today - dt.timedelta(days=7)).isocalendar()
            due.append(("week", f"{year}-W{week:02d}"))
        if today.day == 1:
            prev = today - dt.timedelta(days=1)
            due.append(("month", f"{prev.year}-{prev.month:02d}"))
        return due

    def run_reports(self) -> int:
        code = EXIT_OK
        for period, key in self.due_reports():
            try:
                stats = self.server.fetch_stats(period, key)
                if stats is None:
                    print(f"{period} {key}: 통계 없음, 건너뜀")
                    continue
                narrative = self.analyzer.narrative(period, stats)
                self.server.upload_report(period, key, narrative, self.analyzer.provider_name)
                self._record(date=key, status="ok", stage="report", provider=self.analyzer.provider_name)
                print(f"{period} {key}: 리포트 업로드")
            except Exception as exc:  # noqa: BLE001
                self._record(
                    date=key,
                    status="failed",
                    stage="report",
                    provider=self.analyzer.provider_name,
                    error=str(exc)[:300],
                )
                code = EXIT_FAILED
        return code
