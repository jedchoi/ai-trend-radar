"""기간 · 급상승 · 연속 일수 순수 함수 (BR-S12, BR-S14, BR-S08). PBT 대상."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

RISING_MIN_COUNT = 3
RISING_MIN_RATIO = 2.0
RISING_BASELINE_FLOOR = 0.5
RISING_MAX = 10

_WEEK = re.compile(r"^(\d{4})-W(\d{2})$")
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


def period_key(period: str, day: dt.date) -> str:
    if period == "week":
        year, week, _ = day.isocalendar()
        return f"{year}-W{week:02d}"
    return f"{day.year}-{day.month:02d}"


def period_range(period: str, key: str) -> tuple[dt.date, dt.date]:
    """key → (start, end). 잘못된 key 는 ValueError."""
    if period == "week":
        m = _WEEK.match(key)
        if not m:
            raise ValueError("invalid week key")
        start = dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
        return start, start + dt.timedelta(days=6)
    m = _MONTH.match(key)
    if not m:
        raise ValueError("invalid month key")
    year, month = int(m.group(1)), int(m.group(2))
    start = dt.date(year, month, 1)
    next_start = dt.date(year + (month == 12), month % 12 + 1, 1)
    return start, next_start - dt.timedelta(days=1)


def previous_periods(period: str, key: str, n: int) -> list[str]:
    """key 직전 n 개 기간 key (오래된 것부터)."""
    keys: list[str] = []
    start, _ = period_range(period, key)
    for _ in range(n):
        prev_day = start - dt.timedelta(days=1)
        prev_key = period_key(period, prev_day)
        keys.append(prev_key)
        start, _ = period_range(period, prev_key)
    return list(reversed(keys))


@dataclass(frozen=True)
class Rising:
    keyword: str
    count: int
    baseline: float
    ratio: float


def rising_keywords(counts: dict[str, int], baselines: dict[str, float]) -> list[Rising]:
    """BR-S14: count ≥ 3 이고 count / max(baseline, 0.5) ≥ 2.0, ratio ↓ count ↓ keyword ↑, 최대 10."""
    result = []
    for keyword, count in counts.items():
        if count < RISING_MIN_COUNT:
            continue
        baseline = float(baselines.get(keyword, 0.0))
        ratio = round(count / max(baseline, RISING_BASELINE_FLOOR), 2)
        if ratio >= RISING_MIN_RATIO:
            result.append(Rising(keyword, count, round(baseline, 2), ratio))
    result.sort(key=lambda r: (-r.ratio, -r.count, r.keyword))
    return result[:RISING_MAX]


def streak(present: set[dt.date], day: dt.date) -> int:
    """BR-S08: day 부터 거꾸로 빠짐없이 이어진 일수 (day 가 없으면 0)."""
    count = 0
    while day - dt.timedelta(days=count) in present:
        count += 1
    return count
