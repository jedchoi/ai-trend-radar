"""Hugging Face 수집 (C-P1): Daily Papers · 트렌딩 목록 · 논문 본문. 응답은 형식 검사 후 사용 (NFR-P06)."""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import ValidationError

from radar.models import HubItem, RawPaper
from radar.retry import with_retry

PAGE_SIZE = 10
MAX_PAGES = 20
KIND_PATH = {"model": "/api/models", "dataset": "/api/datasets", "space": "/api/spaces"}


class HFError(RuntimeError):
    pass


def _date(value: Any) -> dt.date | None:
    if isinstance(value, str) and len(value) >= 10:
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _org(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("fullname") or value.get("name")
    return value if isinstance(value, str) else None


def parse_daily_item(item: Any) -> RawPaper | None:
    """Daily Papers 항목 하나 → RawPaper. 모양이 틀리면 None."""
    if not isinstance(item, dict):
        return None
    paper = item.get("paper") if isinstance(item.get("paper"), dict) else None
    if paper is None:
        return None
    authors = [a.get("name") for a in paper.get("authors") or [] if isinstance(a, dict) and a.get("name")]
    try:
        return RawPaper(
            id=paper.get("id"),
            title=paper.get("title") or item.get("title"),
            authors=[str(a)[:200] for a in authors][:60],
            abstract=(paper.get("summary") or item.get("summary") or "")[:10000],
            published_at=_date(paper.get("publishedAt")),
            upvotes=max(int(paper.get("upvotes") or 0), 0),
            ai_summary=paper.get("ai_summary") or None,
            ai_keywords=[k for k in paper.get("ai_keywords") or [] if isinstance(k, str)],
            github_url=paper.get("githubRepo") or None,
            github_stars=paper.get("githubStars"),
            project_url=paper.get("projectPage") or None,
            organization=_org(paper.get("organization") or item.get("organization")),
        )
    except (ValidationError, TypeError, ValueError):
        return None


class HFClient:
    def __init__(self, http: httpx.Client, sleep: Callable[[float], None] = time.sleep) -> None:
        self.http = http
        self.sleep = sleep

    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        try:
            response = with_retry(lambda: self.http.get(path, params=params), self.sleep)
        except httpx.TransportError as exc:
            raise HFError(f"{path}: 연결 실패 ({type(exc).__name__})") from exc
        return response

    def _json(self, path: str, params: dict) -> Any:
        response = self._get(path, params)
        if response.status_code != 200:
            raise HFError(f"{path}: HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise HFError(f"{path}: JSON 아님") from exc

    def daily_papers(self, day: dt.date) -> list[RawPaper]:
        """BR-P02: 10편씩, 짧은 페이지가 오면 멈춤, 최대 20페이지."""
        papers: list[RawPaper] = []
        for page in range(MAX_PAGES):
            items = self._json("/api/daily_papers", {"date": day.isoformat(), "limit": PAGE_SIZE, "p": page})
            if not isinstance(items, list):
                raise HFError("daily_papers: 목록이 아님")
            papers.extend(p for p in (parse_daily_item(i) for i in items) if p is not None)
            if len(items) < PAGE_SIZE:
                break
        seen: set[str] = set()
        return [p for p in papers if not (p.id in seen or seen.add(p.id))]

    def trending(self, kind: str, limit: int) -> list[HubItem]:
        """BR-P03."""
        if limit <= 0:
            return []
        items = self._json(KIND_PATH[kind], {"sort": "trendingScore", "direction": -1, "limit": limit})
        result: list[HubItem] = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            try:
                result.append(
                    HubItem(
                        kind=kind,
                        rank=len(result) + 1,
                        id=item.get("id"),
                        likes=max(int(item.get("likes") or 0), 0),
                        downloads=item.get("downloads"),
                        trending_score=max(float(item.get("trendingScore") or 0), 0.0),
                        task=item.get("pipeline_tag") if kind == "model" else None,
                    )
                )
            except (ValidationError, TypeError, ValueError):
                continue
        return result[:limit]

    def paper_markdown(self, paper_id: str, max_chars: int = 20000) -> str | None:
        """주목 논문 본문 (없으면 None). 실패해도 분석은 초록으로 계속한다."""
        try:
            response = self._get(f"/papers/{paper_id}.md")
        except HFError:
            return None
        if response.status_code != 200 or not response.text.strip():
            return None
        return response.text[:max_chars]
