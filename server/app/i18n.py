"""두 언어 응답 (C-S8, 4주기 FR-38 ~ FR-41, BR-S50 · BR-S51).

응답의 각 항목에 `i18n: {"ko": {...}, "en": {...}}` 를 붙인다 (요약류만).
- 기준 언어 = 원래 값에 한글이 있으면 ko, 없으면 en. i18n[기준 언어] = 원래 값
- 반대 언어 = translations 표의 값 (있을 때만). 기준 언어와 같은 언어의 번역은 쓰지 않는다
- 원문 (제목 · 초록 · 본문) 은 i18n 에 넣지 않는다 — 언제나 원래 값 (FR-41)
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel

from app.repository import Repository
from app.schemas import (
    Digest,
    DigestSummary,
    News,
    NewsBrief,
    Paper,
    PaperBrief,
    PaperWithRelated,
    TrendReport,
)

_HANGUL = re.compile(r"[가-힣]")
PAPER_FIELDS = ("one_liner", "detail", "glossary")
NEWS_FIELDS = ("summary", "key_points")


def base_lang(value: object) -> str:
    """BR-S50."""
    return "ko" if _HANGUL.search(json.dumps(value, ensure_ascii=False)) else "en"


def build_i18n(primary: object, base: dict, translations: dict[str, dict] | None, allowed: tuple[str, ...]) -> dict:
    lang = base_lang(primary)
    other = "en" if lang == "ko" else "ko"
    out: dict[str, dict] = {}
    own = {k: v for k, v in base.items() if v not in (None, "", [], {})}
    if own:
        out[lang] = own
    translated = {k: v for k, v in (translations or {}).get(other, {}).items() if k in allowed}
    if translated:
        out[other] = translated
    return out


def _dump(value):
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_dump(v) for v in value]
    return value


class Localizer:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def papers(self, papers: list[Paper]) -> list[Paper]:
        found = self.repo.translations_all("paper", [p.id for p in papers])
        out = []
        for p in papers:
            base = {"one_liner": p.one_liner, "detail": _dump(p.detail), "glossary": _dump(p.glossary)}
            out.append(p.model_copy(update={"i18n": build_i18n(p.one_liner, base, found.get(p.id), PAPER_FIELDS)}))
        return out

    def briefs(self, briefs: list[PaperBrief]) -> list[PaperBrief]:
        found = self.repo.translations_all("paper", [b.id for b in briefs])
        return [
            b.model_copy(
                update={"i18n": build_i18n(b.one_liner, {"one_liner": b.one_liner}, found.get(b.id), ("one_liner",))}
            )
            for b in briefs
        ]

    def digest(self, digest: Digest) -> Digest:
        key = digest.date.isoformat()
        found = self.repo.translations_all("digest", [key]).get(key)
        i18n = build_i18n(digest.headline, {"headline": digest.headline}, found, ("headline",))
        return digest.model_copy(update={"i18n": i18n, "papers": self.papers(digest.papers)})

    def digest_list(self, items: list[DigestSummary]) -> list[DigestSummary]:
        found = self.repo.translations_all("digest", [d.date.isoformat() for d in items])
        return [
            d.model_copy(
                update={
                    "i18n": build_i18n(
                        d.headline, {"headline": d.headline}, found.get(d.date.isoformat()), ("headline",)
                    )
                }
            )
            for d in items
        ]

    def paper(self, data: PaperWithRelated) -> PaperWithRelated:
        return PaperWithRelated(paper=self.papers([data.paper])[0], related=self.briefs(data.related))

    def news_list(self, items: list[NewsBrief]) -> list[NewsBrief]:
        found = self.repo.translations_all("news", [n.id for n in items])
        return [
            n.model_copy(update={"i18n": build_i18n(n.summary, {"summary": n.summary}, found.get(n.id), ("summary",))})
            for n in items
        ]

    def news(self, news: News) -> News:
        found = self.repo.translations_all("news", [news.id]).get(news.id)
        base = {"summary": news.summary, "key_points": news.key_points}
        return news.model_copy(update={"i18n": build_i18n(news.summary, base, found, NEWS_FIELDS)})

    def report(self, report: TrendReport) -> TrendReport:
        key = f"{report.period}:{report.key}"
        found = self.repo.translations_all("report", [key]).get(key)
        i18n = build_i18n(report.narrative, {"narrative": report.narrative}, found, ("narrative",))
        return report.model_copy(update={"i18n": i18n, "top_papers": self.briefs(report.top_papers)})
