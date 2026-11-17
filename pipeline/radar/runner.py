"""실행 (C-P8): 하루 처리, 빠진 날 채우기, 리포트, 상태 · 실행 기록."""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from radar.analyze import Analyzer
from radar.config import Config, check_server_config
from radar.hf_client import HFClient
from radar.models import DigestPayload, HubItem, RawPaper, Topic
from radar.news import FEED_PATH, Article, analyze_news, extract_article, parse_feed, to_json
from radar.providers import check_ai_config
from radar.publish import ServerClient
from radar.select import select_featured
from radar.topics import classify

KST = ZoneInfo("Asia/Seoul")
BACKFILL_DAYS = 7
BACKFILL_MAX_DAYS = 120
HF_PAUSE_S = 0.5
ORIGINAL_PAUSE_S = 3.0  # NFR-10: 원문 (논문 본문 · 블로그 글) 요청 사이
NEWS_MAX_PER_RUN = 300
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
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.hf = hf
        self.server = server
        self.analyzer = analyzer
        self.now = now
        self.env = os.environ if env is None else env
        self.sleep = sleep
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

    def collect_day(self, day: dt.date, include_hub: bool = True, use_archive: bool = False) -> tuple[list, list]:
        """수집 (BR-P02, BR-P03) 후 원본을 raw/{date}.json 에 보관. use_archive 면 보관본을 먼저 쓴다."""
        raw_path = self.data / "raw" / f"{day.isoformat()}.json"
        if use_archive and raw_path.exists():
            data = json.loads(raw_path.read_text("utf-8"))
            raws = [RawPaper.model_validate(r) for r in data.get("papers", [])]
            hub = [HubItem.model_validate(h) for h in data.get("hub", [])] if include_hub else []
            return raws, hub
        raws = self.hf.daily_papers(day)
        hub: list[HubItem] = []
        if include_hub:
            c = self.config.collect
            hub = (
                self.hf.trending("model", c.models)
                + self.hf.trending("dataset", c.datasets)
                + self.hf.trending("space", c.spaces)
            )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(
            json.dumps(
                {"papers": [r.model_dump(mode="json") for r in raws], "hub": [h.model_dump() for h in hub]},
                ensure_ascii=False,
            ),
            "utf-8",
        )
        return raws, hub

    def analyze_raw(self, day: dt.date, raws: list, hub: list, analyzer: Analyzer) -> tuple[DigestPayload, int]:
        """선별 (BR-P04, BR-P05) 후 분석."""
        topics = {r.id: classify(r.title, r.ai_keywords, r.abstract) for r in raws}
        focus = {Topic(t) for t in self.config.select.focus_topics if t in Topic._value2member_map_}
        featured = select_featured(raws, topics, self.config.select.max_featured, focus)
        return analyzer.analyze_day(day, raws, topics, featured, hub)

    def process_day(self, day: dt.date) -> tuple[DigestPayload, int]:
        stage = "collect"
        try:
            raws, hub = self.collect_day(day)
            stage = "analyze"
            payload, fallbacks = self.analyze_raw(day, raws, hub, self.analyzer)
            stage = "fulltext"
            self.attach_full_text(payload)
            return payload, fallbacks
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
        if dry_run_out is None:
            # 뉴스 먼저 (2026-11-18 사용자 요청). BR-P34: 뉴스 실패는 일일 결과에 영향 없음
            self.run_news(self.config.collect.news_days)
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

    # ---------- 원문 (FR-26, BR-P31) ----------

    def full_text(self, paper_id: str) -> str | None:
        """주목 논문 본문 원문. data/fulltext/{id}.md 에 보관해 한 번만 받는다 (없던 것도 기록)."""
        folder = self.data / "fulltext"
        path, missing = folder / f"{paper_id}.md", folder / f"{paper_id}.none"
        if path.exists():
            return path.read_text("utf-8") or None
        if missing.exists():
            return None
        text = self.hf.paper_markdown(paper_id, self.config.collect.full_text_max_chars)
        self.sleep(ORIGINAL_PAUSE_S)
        folder.mkdir(parents=True, exist_ok=True)
        if text and text.strip():
            path.write_text(text, "utf-8")
            return text
        missing.write_text("", "utf-8")
        return None

    def attach_full_text(self, payload: DigestPayload) -> None:
        if not self.config.collect.full_text:
            return
        for paper in payload.papers:
            if paper.featured:
                try:
                    paper.full_text = self.full_text(paper.id)
                except Exception:  # noqa: BLE001 - NFR-10: 원문 실패는 원문만 비운다
                    paper.full_text = None

    # ---------- 뉴스 (FR-25, BR-P30 ~ BR-P34) ----------

    def _news_seen(self) -> dict[str, str]:
        try:
            return json.loads((self.data / "news_seen.json").read_text())
        except (FileNotFoundError, ValueError):
            return {}

    def _mark_news_seen(self, items: list, provider: str) -> None:
        seen = self._news_seen()
        seen.update({i.id: provider for i in items})
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "news_seen.json").write_text(json.dumps(dict(sorted(seen.items()))))

    def run_news(self, days: int, analyzer: Analyzer | None = None) -> int:
        """기간 안의 새 블로그 글 → 본문 → 분석 → 10건씩 업로드. 업로드된 것만 seen 에 기록.
        analyzer 를 주면 그것으로 분석한다 (백필 1단계: AI 없이 빠르게)."""
        if not self.config.collect.news:
            return EXIT_OK
        analyzer = analyzer or self.analyzer
        started = time.monotonic()
        provider = analyzer.provider_name
        try:
            feed = self.hf.text(FEED_PATH)
            if feed is None:
                raise RuntimeError("RSS 를 받지 못함")
            items = parse_feed(feed)
        except Exception as exc:  # noqa: BLE001
            self._record(stage="news", status="failed", provider=provider, news=0, error=str(exc)[:300])
            print(f"뉴스 수집 실패: {exc}")
            return EXIT_FAILED
        cutoff = self.now() - dt.timedelta(days=days)
        seen = self._news_seen()
        # 처음 보는 글, 또는 AI 없이 올렸던 글을 AI 로 다시 (같은 제공자로는 한 번만)
        todo = [
            i
            for i in items
            if i.published_at >= cutoff and (i.id not in seen or (provider != "none" and seen[i.id] != provider))
        ][:NEWS_MAX_PER_RUN]
        sent, fallbacks, pending = 0, 0, []
        try:
            for n, item in enumerate(todo, start=1):
                html = self.hf.text(urlparse(item.url).path)
                self.sleep(ORIGINAL_PAUSE_S)
                article = extract_article(html) if html else Article()
                payload, fell_back = analyze_news(analyzer, item, article)
                fallbacks += fell_back
                pending.append((item, payload))
                print(f"[뉴스 {n}/{len(todo)}] {item.published_at:%Y-%m-%d} {item.title[:60]}")
                if len(pending) == 10 or n == len(todo):
                    self.server.upload_news(to_json([p for _, p in pending]), provider)
                    self._mark_news_seen([i for i, _ in pending], provider)
                    sent += len(pending)
                    pending = []
        except Exception as exc:  # noqa: BLE001 - BR-P33: 올리지 못한 글은 다음 실행에서 다시
            self._record(
                stage="news",
                status="failed",
                provider=provider,
                news=sent,
                ai_fallbacks=fallbacks,
                error=str(exc)[:300],
            )
            print(f"뉴스 업로드 실패: {exc}")
            return EXIT_FAILED
        self._record(
            stage="news",
            status="ok",
            provider=provider,
            news=sent,
            ai_fallbacks=fallbacks,
            duration_s=round(time.monotonic() - started, 2),
        )
        print(f"뉴스 {sent}건 올림 (기간 {days}일, AI 대체 {fallbacks}건)")
        return EXIT_OK

    # ---------- 번역 (FR-35, BR-P40 ~ BR-P45) ----------

    def run_translate(self, days: int | None = None, max_minutes: int | None = None) -> int:
        """서버의 원본을 읽어 반대 언어 번역을 미리 올린다. AI 가 없으면 건너뛴다."""
        from radar.translate import Translator

        cfg = self.config.translate
        if not cfg.enabled:
            return EXIT_OK
        if self.analyzer.provider is None:
            print("번역 건너뜀: AI 제공자가 없습니다 (provider = none)")
            return EXIT_OK
        started = time.monotonic()
        translator = Translator(
            self.analyzer.provider,
            self.server,
            self.data / "translated.json",
            chunk_chars=cfg.chunk_chars,
            full_text=cfg.full_text,
            max_minutes=cfg.max_minutes if max_minutes is None else max_minutes,
        )
        try:
            result = translator.run(days or cfg.days, self.today_kst())
        except Exception as exc:  # noqa: BLE001 - 번역 실패는 기록만 (논문 · 뉴스 결과와 별개)
            self._record(stage="translate", status="failed", provider=self.analyzer.provider_name, error=str(exc)[:300])
            print(f"번역 실패: {exc}")
            return EXIT_FAILED
        self._record(
            stage="translate",
            status="ok",
            provider=self.analyzer.provider_name,
            translations=result["done"],
            failed=result["failed"],
            stopped=result["stopped"],
            duration_s=round(time.monotonic() - started, 2),
        )
        stopped = ", 시간 상한으로 멈춤" if result["stopped"] else ""
        print(f"번역 {result['done']}건 올림 (실패 {result['failed']}건{stopped})")
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

    # ---------- 백필 (지난 N 일을 실제 데이터로) ----------

    def backfill_dates(self, days: int, until: dt.date | None) -> list[dt.date]:
        """BR-P19: until (기본 한국 시간 어제) 까지 days 일, 오래된 순."""
        end = until or self.today_kst() - dt.timedelta(days=1)
        return [end - dt.timedelta(days=i) for i in range(days - 1, -1, -1)]

    def _analyzed(self) -> dict[str, str]:
        try:
            return json.loads((self.data / "analyzed.json").read_text())
        except (FileNotFoundError, ValueError):
            return {}

    def _mark_analyzed(self, day: dt.date, provider: str) -> None:
        done = self._analyzed()
        done[day.isoformat()] = provider
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "analyzed.json").write_text(json.dumps(dict(sorted(done.items()))))

    def run_backfill(self, days: int = 90, until: dt.date | None = None, reports: bool = True) -> int:
        """1단계: 수집 → AI 없이 바로 업로드 (오래된 날부터, 곧바로 앱에서 볼 수 있게)
        2단계: AI 제공자가 있으면 최근 날부터 분석해 덮어쓰기 (중단해도 다시 돌리면 이어서)
        3단계: 범위의 모든 주 · 월 리포트."""
        problems = self.config_problems()
        if problems:
            for p in problems:
                print(f"설정 문제: {p}")
            return EXIT_CONFIG
        dates = self.backfill_dates(days, until)
        last_day = dates[-1]
        quick = Analyzer(provider=None, max_ai_papers=self.analyzer.max_ai_papers)
        provider = self.analyzer.provider_name
        failed = 0
        print(f"백필 {dates[0]} ~ {last_day} ({len(dates)}일), AI: {provider}")

        # 뉴스 먼저 (AI 없이, 몇 분): 논문 수집 · AI 단계보다 앞에 (BR-P34, 2026-11-18 사용자 요청)
        news_days = (self.today_kst() - dates[0]).days + 1
        if self.config.collect.news:
            self.run_news(news_days, analyzer=quick)

        # 1단계
        collected: list[dt.date] = []
        for i, day in enumerate(dates, start=1):
            started = time.monotonic()
            archived = (self.data / "raw" / f"{day.isoformat()}.json").exists()
            try:
                raws, hub = self.collect_day(day, include_hub=day == last_day, use_archive=True)
            except Exception as exc:  # noqa: BLE001 - 그 날짜만 실패로 기록하고 계속
                failed += 1
                self._record(
                    date=day.isoformat(),
                    status="failed",
                    stage="collect",
                    provider="none",
                    duration_s=round(time.monotonic() - started, 2),
                    error=str(exc)[:300],
                )
                print(f"[{i}/{len(dates)}] {day} 수집 실패: {exc}")
                continue
            if not archived:
                self.sleep(HF_PAUSE_S)  # BR-P20: Hugging Face 에 부담을 주지 않도록
            collected.append(day)
            if self._analyzed().get(day.isoformat()) not in (None, "none"):
                print(f"[{i}/{len(dates)}] {day} 이미 AI 분석됨 ({len(raws)}편)")
                continue
            payload, _ = self.analyze_raw(day, raws, hub, quick)
            self.attach_full_text(payload)
            try:
                self.server.upload_digest(payload)
            except Exception as exc:  # noqa: BLE001 - 업로드 실패 (토큰 · 서버) 는 전체 중단
                self._record(
                    date=day.isoformat(), status="failed", stage="upload", provider="none", error=str(exc)[:300]
                )
                print(f"{day} 업로드 실패: {exc}")
                return EXIT_FAILED
            self._record(
                date=day.isoformat(),
                status="ok",
                stage="backfill",
                provider="none",
                papers=len(payload.papers),
                duration_s=round(time.monotonic() - started, 2),
            )
            print(f"[{i}/{len(dates)}] {day} 올림 ({len(payload.papers)}편)")
        if not failed:
            self._mark_success(last_day)

        # 2단계
        if self.analyzer.provider is not None:
            todo = [d for d in reversed(collected) if self._analyzed().get(d.isoformat()) != provider]
            for i, day in enumerate(todo, start=1):
                started = time.monotonic()
                raws, hub = self.collect_day(day, include_hub=day == last_day, use_archive=True)
                payload, fallbacks = self.analyze_raw(day, raws, hub, self.analyzer)
                units = self.analyzer.last_ai_units
                if units and fallbacks >= units:
                    print(f"{day} AI 호출이 모두 실패했습니다. 제공자 설정 · 로그인 · 한도를 확인하고 다시 실행하세요.")
                    self._record(
                        date=day.isoformat(),
                        status="failed",
                        stage="analyze",
                        provider=provider,
                        ai_fallbacks=fallbacks,
                    )
                    failed += 1
                    break  # 리포트는 규칙 문장으로 계속 만든다
                self.attach_full_text(payload)
                try:
                    self.server.upload_digest(payload)
                except Exception as exc:  # noqa: BLE001
                    print(f"{day} 업로드 실패: {exc}")
                    return EXIT_FAILED
                self._mark_analyzed(day, provider)
                self._record(
                    date=day.isoformat(),
                    status="ok",
                    stage="backfill-ai",
                    provider=provider,
                    papers=len(payload.papers),
                    ai_fallbacks=fallbacks,
                    duration_s=round(time.monotonic() - started, 2),
                )
                print(
                    f"[AI {i}/{len(todo)}] {day} 분석 ({len(payload.papers)}편, 대체 {fallbacks}건, "
                    f"{time.monotonic() - started:.0f}초)"
                )

        # 뉴스를 AI 로 다시 분석해 덮어쓰기 (BR-P34: 실패는 기록만, 논문 결과에 영향 없음)
        if self.config.collect.news and self.analyzer.provider is not None:
            self.run_news(news_days)

        # 3단계
        if reports and self._backfill_reports(dates) != EXIT_OK:
            failed += 1

        # 번역 (3주기): 채운 기간 전체, 짧은 항목 먼저
        self.run_translate(days=(self.today_kst() - dates[0]).days + 1)
        return EXIT_FAILED if failed else EXIT_OK

    def _backfill_reports(self, dates: list[dt.date]) -> int:
        """BR-P22: 범위에 걸친 모든 ISO 주 · 달."""
        weeks = list(dict.fromkeys(f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}" for d in dates))
        months = list(dict.fromkeys(f"{d.year}-{d.month:02d}" for d in dates))
        code = EXIT_OK
        for period, key in [("week", k) for k in weeks] + [("month", k) for k in months]:
            try:
                stats = self.server.fetch_stats(period, key)
                if stats is None:
                    continue
                self.server.upload_report(
                    period, key, self.analyzer.narrative(period, stats), self.analyzer.provider_name
                )
                print(f"리포트 {key} 올림")
            except Exception as exc:  # noqa: BLE001
                print(f"리포트 {key} 실패: {exc}")
                code = EXIT_FAILED
        return code
