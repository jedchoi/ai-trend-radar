"""분석 (C-P4): AI 제공자와 무관한 프롬프트로 요약 · 분류하고, 형식 검사 · 1회 재요청 · 항목별 대체를 한다."""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from radar.models import (
    TOPIC_LABELS_KO,
    AnalyzedPaper,
    BriefItem,
    DetailResponse,
    DigestPayload,
    HeadlineResponse,
    HubItem,
    NarrativeResponse,
    PaperDetail,
    RawPaper,
    Topic,
)

PROMPT_DIR = Path(__file__).parent / "prompts"
BRIEF_BATCH = 10
MAX_KEYWORDS = 8
KEYWORD_LEN = 60
ONE_LINER_LEN = 400
HEADLINE_LEN = 300
RETRY_NOTE = "주의: 직전 응답이 요구한 JSON 형식에 맞지 않았습니다. 설명 없이 형식에 맞는 JSON 만 출력하세요.\n\n"
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_SENTENCE = re.compile(r"^(.+?[.!?])(\s|$)", re.DOTALL)
T = TypeVar("T", bound=BaseModel)


def extract_json(text: str) -> Any:
    """응답에서 JSON 을 꺼낸다: 그대로 → 코드 블록 → 첫 괄호부터 짝이 맞는 끝 괄호까지."""
    candidates = [text.strip()]
    candidates += [m.strip() for m in _FENCE.findall(text)]
    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except ValueError:
            pass
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                value, _ = decoder.raw_decode(text, i)
                return value
            except ValueError:
                continue
    raise ValueError("JSON 을 찾지 못함")


def normalize_keywords(words: list[str]) -> list[str]:
    """BR-P06: 소문자 · 공백 정리 · 60자 · 중복 제거 · 최대 8개."""
    result: list[str] = []
    for word in words:
        norm = " ".join(str(word).lower().split())[:KEYWORD_LEN].strip()
        if norm and norm not in result:
            result.append(norm)
        if len(result) == MAX_KEYWORDS:
            break
    return result


def _cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rstrip()


def none_paper(raw: RawPaper, topic: Topic, featured: bool) -> AnalyzedPaper:
    """BR-P07: AI 없이 만든 결과."""
    if raw.ai_summary and raw.ai_summary.strip():
        one_liner, source = raw.ai_summary.strip(), "hf"
    else:
        match = _SENTENCE.match(raw.abstract.strip())
        first = match.group(1) if match else raw.abstract.strip()
        one_liner, source = (first or raw.title), "abstract"
    return _paper(raw, topic, _cut(one_liner, ONE_LINER_LEN), featured, source)


def _paper(raw: RawPaper, topic: Topic, one_liner: str, featured: bool, source: str, **extra) -> AnalyzedPaper:
    return AnalyzedPaper(
        id=raw.id,
        title=raw.title,
        authors=raw.authors,
        abstract=raw.abstract,
        published_at=raw.published_at,
        upvotes=raw.upvotes,
        topic=topic,
        keywords=normalize_keywords(raw.ai_keywords),
        one_liner=one_liner,
        featured=featured,
        github_url=raw.github_url,
        github_stars=raw.github_stars,
        project_url=raw.project_url,
        organization=raw.organization,
        summary_source=source,
        **extra,
    )


def none_headline(featured: list[AnalyzedPaper]) -> list[str]:
    return [_cut(f"{p.title} — {p.one_liner}", HEADLINE_LEN) for p in featured[:3]]


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.md").read_text("utf-8")


def split_prompt(text: str) -> tuple[str, str]:
    """프롬프트 파일 = system 부분, '---USER---' 줄 아래 = user 틀."""
    system, _, user = text.partition("\n---USER---\n")
    return system.strip(), user.strip()


def fill(template: str, **values: str) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


class Analyzer:
    def __init__(
        self, provider=None, max_ai_papers: int = 60, markdown: Callable[[str], str | None] | None = None
    ) -> None:
        self.provider = provider
        self.max_ai_papers = max_ai_papers
        self.markdown = markdown or (lambda pid: None)
        self.last_ai_units = 0  # 직전 analyze_day 의 AI 작업 수 (한 줄 요약 + 상세 + 세 줄). 전부 실패 판정용

    @property
    def provider_name(self) -> str:
        return self.provider.name if self.provider else "none"

    # ---------- AI 호출 공통 ----------

    def _ask(self, prompt: str, values: dict[str, str], retry: bool = False) -> Any:
        system, user = split_prompt(load_prompt(prompt))
        text = self.provider.complete(fill(system, **values), (RETRY_NOTE if retry else "") + fill(user, **values))
        return extract_json(text)

    def _ask_model(self, prompt: str, values: dict[str, str], model: type[T]) -> T | None:
        """BR-P10: 형식 위반 · 오류면 1회 다시 요청."""
        for attempt in range(2):
            try:
                return model.model_validate(self._ask(prompt, values, retry=attempt > 0))
            except Exception:  # noqa: BLE001, S112 - 제공자 오류 · 형식 위반 모두 재요청 · 대체 대상 (BR-P10)
                continue
        return None

    # ---------- 하루 분석 ----------

    def analyze_day(
        self, day: dt.date, raws: list[RawPaper], topics: dict[str, Topic], featured_ids: list[str], hub: list[HubItem]
    ) -> tuple[DigestPayload, int]:
        featured_set = set(featured_ids)
        papers = {r.id: none_paper(r, topics.get(r.id, Topic.OTHER), r.id in featured_set) for r in raws}
        fallbacks = 0
        self.last_ai_units = 0
        if self.provider and raws:
            ai_ids = {r.id for r in sorted(raws, key=lambda r: (-r.upvotes, r.id))[: self.max_ai_papers]}
            ai_raws = [r for r in raws if r.id in ai_ids]
            self.last_ai_units = len(ai_raws) + sum(r.id in featured_set for r in ai_raws)
            fallbacks += self._briefs(ai_raws, papers)
            for raw in ai_raws:
                if raw.id in featured_set:
                    fallbacks += self._detail(raw, papers)
        featured = [papers[i] for i in featured_ids if i in papers]
        headline = none_headline(featured)
        if self.provider and featured:
            self.last_ai_units += 1
            got = self._ask_model(
                "headline",
                {
                    "PAPERS_JSON": json.dumps(
                        [{"title": p.title, "topic": p.topic.value, "summary": p.one_liner} for p in featured],
                        ensure_ascii=False,
                    )
                },
                HeadlineResponse,
            )
            if got is None:
                fallbacks += 1
            else:
                headline = got.headline
        payload = DigestPayload(
            date=day, headline=headline, provider=self.provider_name, papers=[papers[r.id] for r in raws], hub=hub
        )
        return payload, fallbacks

    def _briefs(self, raws: list[RawPaper], papers: dict[str, AnalyzedPaper]) -> int:
        """모든 AI 대상 논문의 주제 · 한 줄 요약 (10편씩). 실패한 항목 수를 돌려준다."""
        failed = 0
        for start in range(0, len(raws), BRIEF_BATCH):
            pending = {r.id: r for r in raws[start : start + BRIEF_BATCH]}
            for attempt in range(2):
                if not pending:
                    break
                body = [
                    {"id": r.id, "title": r.title, "abstract": _cut(r.abstract, 1500), "keywords": r.ai_keywords[:8]}
                    for r in pending.values()
                ]
                try:
                    data = self._ask("brief", {"PAPERS_JSON": json.dumps(body, ensure_ascii=False)}, retry=attempt > 0)
                    items = data.get("papers", []) if isinstance(data, dict) else []
                except Exception:  # noqa: BLE001
                    items = []
                for item in items:
                    try:
                        brief = BriefItem.model_validate(item)
                    except ValidationError:
                        continue
                    if brief.id in pending:
                        raw = pending.pop(brief.id)
                        papers[raw.id] = _paper(raw, brief.topic, brief.one_liner, papers[raw.id].featured, "ai")
            failed += len(pending)
        return failed

    def _detail(self, raw: RawPaper, papers: dict[str, AnalyzedPaper]) -> int:
        text = self.markdown(raw.id) or raw.abstract
        got = self._ask_model("detail", {"ID": raw.id, "TITLE": raw.title, "TEXT": text}, DetailResponse)
        if got is None or got.id != raw.id:
            return 1
        papers[raw.id] = _paper(
            raw,
            got.topic,
            got.one_liner,
            True,
            "ai",
            detail=PaperDetail(what=got.what, novelty=got.novelty, why=got.why, apply=got.apply),
            glossary=got.glossary,
        )
        return 0

    # ---------- 리포트 ----------

    def narrative(self, period: str, stats: dict) -> str:
        """BR-P17: AI 해석, 실패하거나 none 이면 규칙 문장."""
        if self.provider:
            got = self._ask_model(
                "report",
                {"PERIOD": "주간" if period == "week" else "월간", "STATS_JSON": json.dumps(stats, ensure_ascii=False)},
                NarrativeResponse,
            )
            if got is not None:
                return got.narrative
        return rule_narrative(period, stats)


def rule_narrative(period: str, stats: dict) -> str:
    span = "이번 주" if period == "week" else "이번 달"
    topics = [t for t in stats.get("topics", []) if t.get("count", 0) > 0][:2]
    parts = [f"{span} 수집한 논문은 {stats.get('paper_count', 0)}편이다."]
    if topics:
        names = ", ".join(f"{TOPIC_LABELS_KO.get(Topic(t['topic']), t['topic'])} {t['count']}편" for t in topics)
        parts.append(f"가장 많은 주제는 {names}.")
    rising = [r["keyword"] for r in stats.get("rising_keywords", [])][:3]
    if rising:
        parts.append(f"급상승 키워드는 {', '.join(rising)}.")
    return " ".join(parts)
