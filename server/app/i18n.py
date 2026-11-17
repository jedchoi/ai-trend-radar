"""언어별 응답 (C-S8, BR-S40): 미리 저장한 번역 (translations 표) 을 응답 모델에 덮어쓴다.

원래 표는 원문 (영어) 과 AI 요약 (한국어) 을 그대로 두고, 반대 언어 값만 번역으로 둔다.
lang 이 없으면 아무것도 바꾸지 않는다 (호환).
"""

from __future__ import annotations

from pydantic import BaseModel

from app.repository import Repository
from app.schemas import (
    Digest,
    DigestSummary,
    GlossaryItem,
    News,
    NewsBrief,
    Paper,
    PaperBrief,
    PaperDetail,
    PaperWithRelated,
    TrendReport,
)

PAPER_FIELDS = ("title", "one_liner", "abstract", "full_text", "detail", "glossary")
BRIEF_FIELDS = ("title", "one_liner")
NEWS_FIELDS = ("title", "summary", "key_points", "content")
NEWS_BRIEF_FIELDS = ("title", "summary")


def _apply[M: BaseModel](model: M, fields: dict | None, allowed: tuple[str, ...], flag: bool = False) -> M:
    update = {k: v for k, v in (fields or {}).items() if k in allowed}
    if "detail" in update:
        update["detail"] = PaperDetail.model_validate(update["detail"])
    if "glossary" in update:
        update["glossary"] = [GlossaryItem.model_validate(g) for g in update["glossary"]]
    if flag:
        update["untranslated"] = fields is None
    return model.model_copy(update=update)


class Localizer:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def papers(self, papers: list[Paper], lang: str, light: bool = True) -> list[Paper]:
        found = self.repo.translations("paper", [p.id for p in papers], lang, light=light)
        return [_apply(p, found.get(p.id), PAPER_FIELDS, flag=True) for p in papers]

    def briefs(self, briefs: list[PaperBrief], lang: str | None) -> list[PaperBrief]:
        if not lang:
            return briefs
        found = self.repo.translations("paper", [b.id for b in briefs], lang, light=True)
        return [_apply(b, found.get(b.id), BRIEF_FIELDS) for b in briefs]

    def digest(self, digest: Digest, lang: str | None) -> Digest:
        if not lang:
            return digest
        head = self.repo.translations("digest", [digest.date.isoformat()], lang).get(digest.date.isoformat())
        digest = _apply(digest, head, ("headline",), flag=True)
        return digest.model_copy(update={"papers": self.papers(digest.papers, lang)})

    def digest_list(self, items: list[DigestSummary], lang: str | None) -> list[DigestSummary]:
        if not lang:
            return items
        found = self.repo.translations("digest", [d.date.isoformat() for d in items], lang)
        return [_apply(d, found.get(d.date.isoformat()), ("headline",)) for d in items]

    def paper(self, data: PaperWithRelated, lang: str | None) -> PaperWithRelated:
        if not lang:
            return data
        return PaperWithRelated(
            paper=self.papers([data.paper], lang, light=False)[0], related=self.briefs(data.related, lang)
        )

    def news_list(self, items: list[NewsBrief], lang: str | None) -> list[NewsBrief]:
        if not lang:
            return items
        found = self.repo.translations("news", [n.id for n in items], lang, light=True)
        return [_apply(n, found.get(n.id), NEWS_BRIEF_FIELDS) for n in items]

    def news(self, news: News, lang: str | None) -> News:
        if not lang:
            return news
        found = self.repo.translations("news", [news.id], lang).get(news.id)
        return _apply(news, found, NEWS_FIELDS, flag=True)

    def report(self, report: TrendReport, lang: str | None) -> TrendReport:
        if not lang:
            return report
        key = f"{report.period}:{report.key}"
        found = self.repo.translations("report", [key], lang).get(key)
        report = _apply(report, found, ("narrative",), flag=True)
        return report.model_copy(update={"top_papers": self.briefs(report.top_papers, lang)})
