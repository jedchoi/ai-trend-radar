"""업로드 API (C-S2). 모든 경로가 토큰 인증 (BR-S01)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.schemas import (
    DigestIngest,
    IngestResult,
    NewsIngest,
    NewsResult,
    ReportIngest,
    ReportResult,
    TranslationIngest,
    TranslationResult,
)
from app.security import client_ip, require_ingest_token

router = APIRouter(prefix="/api/v1/ingest", dependencies=[Depends(require_ingest_token)])


@router.post("/daily", response_model=IngestResult)
def ingest_daily(request: Request, digest: DigestIngest) -> IngestResult:
    count = request.app.state.repo.upsert_digest(digest, client_ip(request))
    return IngestResult(date=digest.date, papers=count)


@router.post("/report", response_model=ReportResult)
def ingest_report(request: Request, report: ReportIngest) -> ReportResult:
    request.app.state.repo.upsert_report(
        report.period, report.key, report.narrative, report.provider, client_ip(request)
    )
    return ReportResult(period=report.period, key=report.key)


@router.post("/news", response_model=NewsResult)
def ingest_news(request: Request, news: NewsIngest) -> NewsResult:
    return NewsResult(news=request.app.state.repo.upsert_news(news, client_ip(request)))


@router.post("/translations", response_model=TranslationResult)
def ingest_translations(request: Request, body: TranslationIngest) -> TranslationResult:
    return TranslationResult(translations=request.app.state.repo.upsert_translations(body, client_ip(request)))
