"""트렌드 통계 (C-S5): BR-S12 ~ BR-S20."""

from __future__ import annotations

import datetime as dt

from app.periods import period_key, period_range, previous_periods, rising_keywords, streak
from app.repository import Repository
from app.schemas import (
    HubNew,
    HubSteady,
    Periods,
    RisingKeyword,
    Topic,
    TopicCount,
    TopicSeries,
    TrendReport,
)

BASELINE_PERIODS = 4
HUB_LIST_MAX = 10
PERIODS_LIST_MAX = 12
TOPIC_ORDER = {t.value: i for i, t in enumerate(Topic)}


class TrendService:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def latest_key(self, period: str) -> str | None:
        latest = self.repo.latest_date()
        return period_key(period, latest) if latest else None

    def period_stats(self, period: str, key: str) -> TrendReport | None:
        start, end = period_range(period, key)
        if not self.repo.has_digest_between(start, end):
            return None
        prev_key = previous_periods(period, key, 1)[0]
        prev_start, prev_end = period_range(period, prev_key)
        base_keys = previous_periods(period, key, BASELINE_PERIODS)

        return TrendReport(
            period=period,
            key=key,
            start=start,
            end=end,
            paper_count=self.repo.paper_count(start, end),
            topics=self._topics(start, end, prev_start, prev_end),
            **self._rising(period, start, end, base_keys),
            top_papers=self.repo.top_papers(start, end),
            **self._hub(start, end),
            **self._narrative(period, key),
        )

    def _topics(self, start, end, prev_start, prev_end) -> list[TopicCount]:
        """BR-S13."""
        now = self.repo.topic_counts(start, end)
        prev = self.repo.topic_counts(prev_start, prev_end)
        rows = [
            TopicCount(topic=t, count=now.get(t, 0), prev_count=prev.get(t, 0), delta=now.get(t, 0) - prev.get(t, 0))
            for t in set(now) | set(prev)
        ]
        rows.sort(key=lambda r: (-r.count, -r.prev_count, TOPIC_ORDER[r.topic.value]))
        return rows

    def _rising(self, period, start, end, base_keys) -> dict:
        """BR-S14 · BR-S15."""
        dates = self.repo.digest_dates()
        base_start = period_range(period, base_keys[0])[0]
        ready = bool(dates) and dates[0] <= base_start
        if not ready:
            return {"rising_keywords": [], "baseline_ready": False}
        totals: dict[str, int] = {}
        for k in base_keys:
            s, e = period_range(period, k)
            for word, n in self.repo.keyword_counts(s, e).items():
                totals[word] = totals.get(word, 0) + n
        baselines = {w: n / BASELINE_PERIODS for w, n in totals.items()}
        rising = rising_keywords(self.repo.keyword_counts(start, end), baselines)
        return {
            "rising_keywords": [RisingKeyword(**r.__dict__) for r in rising],
            "baseline_ready": True,
        }

    def _hub(self, start: dt.date, end: dt.date) -> dict:
        """BR-S17 · BR-S18."""
        history = self.repo.hub_history(until=end)
        new, last_day = [], None
        for (kind, item_id), dates in history.items():
            in_period = sorted(d for d in dates if d >= start)
            if not in_period:
                continue
            last_day = max(last_day or in_period[-1], in_period[-1])
            first = min(dates)
            if first >= start:
                new.append(HubNew(kind=kind, id=item_id, first_seen=first, days=len(in_period)))
        new.sort(key=lambda h: (-h.days, h.first_seen, h.kind, h.id))
        steady = []
        if last_day is not None:
            steady = [
                HubSteady(kind=kind, id=item_id, streak_days=streak(dates, last_day))
                for (kind, item_id), dates in history.items()
                if last_day in dates
            ]
            steady.sort(key=lambda h: (-h.streak_days, h.kind, h.id))
        return {"hub_new": new[:HUB_LIST_MAX], "hub_steady": steady[:HUB_LIST_MAX]}

    def _narrative(self, period: str, key: str) -> dict:
        report = self.repo.get_report(period, key)
        return {"narrative": report[0], "narrative_provider": report[1]} if report else {}

    def topic_series(self, weeks: int) -> TopicSeries:
        """BR-S19."""
        latest = self.repo.latest_date()
        if latest is None:
            return TopicSeries(weeks=[], topics={})
        last_key = period_key("week", latest)
        keys = [*previous_periods("week", last_key, weeks - 1), last_key]
        series: dict[str, list[int]] = {t.value: [] for t in Topic}
        for k in keys:
            counts = self.repo.topic_counts(*period_range("week", k))
            for t in Topic:
                series[t.value].append(counts.get(t.value, 0))
        return TopicSeries(weeks=keys, topics=series)

    def available_periods(self) -> Periods:
        dates = sorted(self.repo.digest_dates(), reverse=True)
        weeks = list(dict.fromkeys(period_key("week", d) for d in dates))[:PERIODS_LIST_MAX]
        months = list(dict.fromkeys(period_key("month", d) for d in dates))[:PERIODS_LIST_MAX]
        return Periods(weeks=weeks, months=months)
