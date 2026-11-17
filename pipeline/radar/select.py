"""주목 논문 선별 (C-P3, BR-P05)."""

from __future__ import annotations

from radar.models import RawPaper, Topic

FOCUS_BONUS = 30
CODE_BONUS = 15


def score(paper: RawPaper, topic: Topic, focus: set[Topic]) -> int:
    return paper.upvotes + (FOCUS_BONUS if topic in focus else 0) + (CODE_BONUS if paper.github_url else 0)


def select_featured(papers: list[RawPaper], topics: dict[str, Topic], n: int, focus: set[Topic]) -> list[str]:
    ranked = sorted(papers, key=lambda p: (-score(p, topics.get(p.id, Topic.OTHER), focus), -p.upvotes, p.id))
    return [p.id for p in ranked[: max(n, 0)]]
