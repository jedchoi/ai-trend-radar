"""공개 읽기 API (C-S1). GET 만 제공 (SECURITY-08)."""

from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request

from app.schemas import (
    MONTH_KEY_PATTERN,
    NEWS_ID_PATTERN,
    PAPER_ID_PATTERN,
    WEEK_KEY_PATTERN,
    Digest,
    DigestList,
    Health,
    News,
    NewsList,
    PaperWithRelated,
    Periods,
    SearchResult,
    Topic,
    TopicSeries,
    TrendReport,
)

router = APIRouter(prefix="/api/v1")


def _repo(request: Request):
    return request.app.state.repo


def _trends(request: Request):
    return request.app.state.trends


def _i18n(request: Request):
    return request.app.state.i18n


def _found(value):
    if value is None:
        raise HTTPException(status_code=404)
    return value


@router.get("/health", response_model=Health)
def health(request: Request) -> Health:
    return Health(status="ok", latest_date=_repo(request).latest_date())


@router.get("/digests", response_model=DigestList)
def list_digests(request: Request, limit: Annotated[int, Query(ge=1, le=90)] = 30) -> DigestList:
    return DigestList(items=_i18n(request).digest_list(_repo(request).list_digests(limit)))


@router.get("/digests/latest", response_model=Digest)
def latest_digest(request: Request) -> Digest:
    latest = _found(_repo(request).latest_date())
    return _i18n(request).digest(_found(_repo(request).get_digest(latest)))


@router.get("/digests/{day}", response_model=Digest)
def get_digest(request: Request, day: dt.date) -> Digest:
    return _i18n(request).digest(_found(_repo(request).get_digest(day)))


@router.get("/papers/{paper_id}", response_model=PaperWithRelated)
def get_paper(request: Request, paper_id: Annotated[str, Path(pattern=PAPER_ID_PATTERN)]) -> PaperWithRelated:
    paper = _found(_repo(request).get_paper(paper_id))
    return _i18n(request).paper(PaperWithRelated(paper=paper, related=_repo(request).related_papers(paper)))


@router.get("/papers", response_model=SearchResult)
def search_papers(
    request: Request,
    q: Annotated[str | None, Query(max_length=300)] = None,
    topic: Topic | None = None,
    since: dt.date | None = None,
    until: dt.date | None = None,
    featured: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> SearchResult:
    items, total = _repo(request).search_papers(
        q, topic.value if topic else None, since, until, featured, limit, offset
    )
    return SearchResult(items=_i18n(request).briefs(items), total=total)


@router.get("/news", response_model=NewsList)
def list_news(
    request: Request,
    q: Annotated[str | None, Query(max_length=300)] = None,
    topic: Topic | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> NewsList:
    items, total = _repo(request).list_news(q, topic.value if topic else None, limit, offset)
    return NewsList(items=_i18n(request).news_list(items), total=total)


@router.get("/news/{news_id:path}", response_model=News)
def get_news(request: Request, news_id: Annotated[str, Path(pattern=NEWS_ID_PATTERN)]) -> News:
    return _i18n(request).news(_found(_repo(request).get_news(news_id)))


@router.get("/trends/periods", response_model=Periods)
def periods(request: Request) -> Periods:
    return _trends(request).available_periods()


@router.get("/trends/series", response_model=TopicSeries)
def series(request: Request, weeks: Annotated[int, Query(ge=1, le=26)] = 12) -> TopicSeries:
    return _trends(request).topic_series(weeks)


def _report(request: Request, period: str, key: str | None) -> TrendReport:
    key = _found(key)
    try:
        report = _found(_trends(request).period_stats(period, key))
    except ValueError as exc:  # 53주가 없는 해의 W53 등
        raise HTTPException(status_code=422) from exc
    return _i18n(request).report(report)


@router.get("/trends/weekly/latest", response_model=TrendReport)
def weekly_latest(request: Request) -> TrendReport:
    return _report(request, "week", _trends(request).latest_key("week"))


@router.get("/trends/weekly/{key}", response_model=TrendReport)
def weekly(request: Request, key: Annotated[str, Path(pattern=WEEK_KEY_PATTERN)]) -> TrendReport:
    return _report(request, "week", key)


@router.get("/trends/monthly/latest", response_model=TrendReport)
def monthly_latest(request: Request) -> TrendReport:
    return _report(request, "month", _trends(request).latest_key("month"))


@router.get("/trends/monthly/{key}", response_model=TrendReport)
def monthly(request: Request, key: Annotated[str, Path(pattern=MONTH_KEY_PATTERN)]) -> TrendReport:
    return _report(request, "month", key)
