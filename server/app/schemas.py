"""API 계약 (Contract) — 세 unit 이 공유하는 요청 · 응답 형식의 정본.

규칙: 필드는 추가만 한다 (NFR-07). 업로드 형식 위반은 422 (BR-S04).
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

PAPER_ID_PATTERN = r"^[A-Za-z0-9._-]{1,40}$"
HUB_ID_PATTERN = r"^[A-Za-z0-9._-]{1,96}/[A-Za-z0-9._-]{1,96}$"
WEEK_KEY_PATTERN = r"^\d{4}-W(0[1-9]|[1-4]\d|5[0-3])$"
MONTH_KEY_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
NEWS_ID_PATTERN = r"^[a-z0-9][a-z0-9._-]{0,99}(/[a-z0-9][a-z0-9._-]{0,149})?$"
MIN_DATE = dt.date(2020, 1, 1)
FULL_TEXT_MAX = 200_000
RAW_MAX_BYTES = 100_000


class Topic(StrEnum):
    LLM_REASONING = "llm-reasoning"
    AGENTS = "agents"
    MULTIMODAL_VISION = "multimodal-vision"
    IMAGE_VIDEO_GEN = "image-video-gen"
    ROBOTICS_PHYSICAL = "robotics-physical"
    SPEECH_AUDIO = "speech-audio"
    TRAINING_OPTIMIZATION = "training-optimization"
    EVALUATION_BENCHMARK = "evaluation-benchmark"
    OTHER = "other"


class SummarySource(StrEnum):
    AI = "ai"
    HF = "hf"
    ABSTRACT = "abstract"


HubKind = Literal["model", "dataset", "space"]
Period = Literal["week", "month"]

Text = Annotated[str, StringConstraints(strip_whitespace=True)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Url = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500, pattern=r"^https?://\S+$")]
Keyword = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=60)]
FullText = Annotated[str, StringConstraints(max_length=FULL_TEXT_MAX)]


def _check_raw(value: dict | None) -> dict | None:
    """BR-S31: 원본 JSON 은 100 KB 까지."""
    import json

    if value is not None and len(json.dumps(value, ensure_ascii=False).encode()) > RAW_MAX_BYTES:
        raise ValueError("source_raw too large")
    return value


def _check_date(value: dt.date) -> dt.date:
    today = dt.datetime.now(dt.UTC).date()
    if value < MIN_DATE or value > today + dt.timedelta(days=1):
        raise ValueError("date out of range")
    return value


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaperDetail(Strict):
    what: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
    novelty: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
    why: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
    apply: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]


class GlossaryItem(Strict):
    term: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    explanation: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class PaperIn(Strict):
    id: Annotated[str, StringConstraints(pattern=PAPER_ID_PATTERN)]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    authors: list[ShortText] = Field(default_factory=list, max_length=60)
    abstract: Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)] = ""
    published_at: dt.date | None = None
    upvotes: int = Field(default=0, ge=0, le=100000)
    topic: Topic
    keywords: list[Keyword] = Field(default_factory=list, max_length=15)
    one_liner: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
    featured: bool = False
    detail: PaperDetail | None = None
    glossary: list[GlossaryItem] = Field(default_factory=list, max_length=5)
    github_url: Url | None = None
    github_stars: int | None = Field(default=None, ge=0)
    project_url: Url | None = None
    organization: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    summary_source: SummarySource = SummarySource.HF
    full_text: FullText | None = None
    source_raw: dict | None = None

    @field_validator("keywords")
    @classmethod
    def _dedupe_keywords(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @field_validator("source_raw")
    @classmethod
    def _raw_size(cls, value: dict | None) -> dict | None:
        return _check_raw(value)


class HubItemIn(Strict):
    kind: HubKind
    rank: int = Field(ge=1, le=50)
    id: Annotated[str, StringConstraints(pattern=HUB_ID_PATTERN)]
    likes: int = Field(default=0, ge=0)
    downloads: int | None = Field(default=None, ge=0)
    trending_score: float = Field(default=0.0, ge=0)
    task: Annotated[str, StringConstraints(max_length=80)] | None = None


class DigestIngest(Strict):
    date: dt.date
    headline: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]] = Field(
        default_factory=list, max_length=3
    )
    provider: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,30}$")] = "none"
    papers: list[PaperIn] = Field(default_factory=list, max_length=200)
    hub: list[HubItemIn] = Field(default_factory=list, max_length=60)

    @field_validator("date")
    @classmethod
    def _date_range(cls, value: dt.date) -> dt.date:
        return _check_date(value)

    @field_validator("papers")
    @classmethod
    def _unique_papers(cls, value: list[PaperIn]) -> list[PaperIn]:
        if len({p.id for p in value}) != len(value):
            raise ValueError("duplicate paper id")
        return value

    @field_validator("hub")
    @classmethod
    def _unique_hub(cls, value: list[HubItemIn]) -> list[HubItemIn]:
        if len({(h.kind, h.id) for h in value}) != len(value):
            raise ValueError("duplicate hub item")
        return value


class ReportIngest(Strict):
    period: Period
    key: str
    narrative: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]
    provider: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,30}$")] = "none"

    @field_validator("key")
    @classmethod
    def _key_matches_period(cls, value: str, info) -> str:
        import re

        pattern = WEEK_KEY_PATTERN if info.data.get("period") == "week" else MONTH_KEY_PATTERN
        if not re.fullmatch(pattern, value):
            raise ValueError("invalid period key")
        return value


class NewsIn(Strict):
    id: Annotated[str, StringConstraints(pattern=NEWS_ID_PATTERN)]
    url: Url
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    published_at: dt.datetime
    organization: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    authors: list[ShortText] = Field(default_factory=list, max_length=30)
    image_url: Url | None = None
    content: FullText = ""
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)]
    key_points: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]] = Field(
        default_factory=list, max_length=6
    )
    keywords: list[Keyword] = Field(default_factory=list, max_length=15)
    topic: Topic = Topic.OTHER
    summary_source: SummarySource = SummarySource.AI
    source_raw: dict | None = None

    @field_validator("keywords")
    @classmethod
    def _dedupe_keywords(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @field_validator("source_raw")
    @classmethod
    def _raw_size(cls, value: dict | None) -> dict | None:
        return _check_raw(value)


class NewsIngest(Strict):
    provider: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,30}$")] = "none"
    items: list[NewsIn] = Field(min_length=1, max_length=20)

    @field_validator("items")
    @classmethod
    def _unique(cls, value: list[NewsIn]) -> list[NewsIn]:
        if len({n.id for n in value}) != len(value):
            raise ValueError("duplicate news id")
        return value


# ---------- 번역 (3주기, BR-S41) ----------

Lang = Literal["ko", "en"]
TranslationKind = Literal["paper", "news", "digest", "report"]
REPORT_KEY_PATTERN = r"^(week:\d{4}-W(0[1-9]|[1-4]\d|5[0-3])|month:\d{4}-(0[1-9]|1[0-2]))$"
DATE_KEY_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
Line300 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class PaperTranslation(Strict):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)] | None = None
    one_liner: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)] | None = None
    # 논문 원문 (초록 · 본문) 은 번역하지 않는다 (FR-34 개정 2026-11-18): abstract · full_text 를 보내면 422
    detail: PaperDetail | None = None
    glossary: list[GlossaryItem] | None = Field(default=None, max_length=5)


class NewsTranslation(Strict):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)] | None = None
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)] | None = None
    key_points: list[Line300] | None = Field(default=None, max_length=6)
    content: Annotated[str, StringConstraints(min_length=1, max_length=FULL_TEXT_MAX)] | None = None


class DigestTranslation(Strict):
    headline: list[Line300] | None = Field(default=None, min_length=1, max_length=3)


class ReportTranslation(Strict):
    narrative: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)] | None = None


TRANSLATION_FIELDS: dict[str, type[Strict]] = {
    "paper": PaperTranslation,
    "news": NewsTranslation,
    "digest": DigestTranslation,
    "report": ReportTranslation,
}
TRANSLATION_KEYS = {
    "paper": PAPER_ID_PATTERN,
    "news": NEWS_ID_PATTERN,
    "digest": DATE_KEY_PATTERN,
    "report": REPORT_KEY_PATTERN,
}


class TranslationIn(Strict):
    kind: TranslationKind
    key: Annotated[str, StringConstraints(max_length=260)]
    lang: Lang
    fields: dict

    @model_validator(mode="after")
    def _check(self) -> TranslationIn:
        import re

        if not re.fullmatch(TRANSLATION_KEYS[self.kind], self.key):
            raise ValueError("invalid key for kind")
        if self.kind == "digest":
            dt.date.fromisoformat(self.key)
        parsed = TRANSLATION_FIELDS[self.kind].model_validate(self.fields)
        fields = parsed.model_dump(exclude_none=True)
        if not fields:
            raise ValueError("empty fields")
        self.fields = fields
        return self


class TranslationIngest(Strict):
    provider: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{1,30}$")] = "none"
    items: list[TranslationIn] = Field(min_length=1, max_length=50)


class TranslationResult(BaseModel):
    translations: int


# ---------- 응답 ----------


class Paper(PaperIn):
    model_config = ConfigDict(extra="ignore")
    date: dt.date
    hf_url: str
    arxiv_url: str
    has_full_text: bool = False
    source_raw: dict | None = Field(default=None, exclude=True)  # BR-S31: 응답에 넣지 않는다
    untranslated: bool = False  # BR-S40: lang 을 줬는데 번역이 없음


class PaperBrief(BaseModel):
    id: str
    title: str
    date: dt.date
    topic: Topic
    one_liner: str
    upvotes: int
    featured: bool
    github_url: str | None = None


class HubItem(HubItemIn):
    model_config = ConfigDict(extra="ignore")
    is_new: bool
    streak_days: int
    url: str


class Digest(BaseModel):
    date: dt.date
    headline: list[str]
    provider: str
    papers: list[Paper]
    hub: list[HubItem]
    untranslated: bool = False


class DigestSummary(BaseModel):
    date: dt.date
    headline: list[str]
    paper_count: int
    featured_count: int


class DigestList(BaseModel):
    items: list[DigestSummary]


class PaperWithRelated(BaseModel):
    paper: Paper
    related: list[PaperBrief]


class SearchResult(BaseModel):
    items: list[PaperBrief]
    total: int


class TopicCount(BaseModel):
    topic: Topic
    count: int
    prev_count: int
    delta: int


class RisingKeyword(BaseModel):
    keyword: str
    count: int
    baseline: float
    ratio: float


class HubNew(BaseModel):
    kind: HubKind
    id: str
    first_seen: dt.date
    days: int


class HubSteady(BaseModel):
    kind: HubKind
    id: str
    streak_days: int


class TrendReport(BaseModel):
    period: Period
    key: str
    start: dt.date
    end: dt.date
    paper_count: int
    topics: list[TopicCount]
    rising_keywords: list[RisingKeyword]
    baseline_ready: bool
    top_papers: list[PaperBrief]
    hub_new: list[HubNew]
    hub_steady: list[HubSteady]
    narrative: str | None = None
    narrative_provider: str | None = None
    untranslated: bool = False


class TopicSeries(BaseModel):
    weeks: list[str]
    topics: dict[str, list[int]]


class Periods(BaseModel):
    weeks: list[str]
    months: list[str]


class Health(BaseModel):
    status: str
    latest_date: dt.date | None


class IngestResult(BaseModel):
    date: dt.date
    papers: int


class ReportResult(BaseModel):
    period: Period
    key: str


class NewsBrief(BaseModel):
    id: str
    title: str
    url: str
    published_at: dt.datetime
    organization: str | None = None
    image_url: str | None = None
    summary: str
    topic: Topic
    keywords: list[str]


class News(NewsBrief):
    authors: list[str]
    content: str
    key_points: list[str]
    summary_source: SummarySource
    provider: str
    untranslated: bool = False


class NewsList(BaseModel):
    items: list[NewsBrief]
    total: int


class NewsResult(BaseModel):
    news: int
