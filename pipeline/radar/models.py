"""파이프라인 형식. 업로드 형식 (AnalyzedPaper, DigestPayload) 은 서버 계약 `server/app/schemas.py` 와 같은 필드다.

계약 일치는 tests/test_contract.py 가 서버 스키마로 직접 검사한다.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


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


TOPIC_LABELS_KO = {
    Topic.LLM_REASONING: "LLM · 추론",
    Topic.AGENTS: "에이전트",
    Topic.MULTIMODAL_VISION: "멀티모달 · 비전",
    Topic.IMAGE_VIDEO_GEN: "이미지 · 영상 생성",
    Topic.ROBOTICS_PHYSICAL: "로보틱스 · 피지컬 AI",
    Topic.SPEECH_AUDIO: "음성 · 오디오",
    Topic.TRAINING_OPTIMIZATION: "학습 · 최적화",
    Topic.EVALUATION_BENCHMARK: "평가 · 벤치마크",
    Topic.OTHER: "기타",
}

HubKind = Literal["model", "dataset", "space"]
HUB_ID_PATTERN = r"^[A-Za-z0-9._-]{1,96}/[A-Za-z0-9._-]{1,96}$"
PAPER_ID_PATTERN = r"^[A-Za-z0-9._-]{1,40}$"

Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
Para = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
Url = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500, pattern=r"^https?://\S+$")]


class RawPaper(BaseModel):
    """Hugging Face Daily Papers 항목에서 쓰는 필드만 (C-P1 이 방어적으로 채운다)."""

    id: Annotated[str, StringConstraints(pattern=PAPER_ID_PATTERN)]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    published_at: dt.date | None = None
    upvotes: int = 0
    ai_summary: str | None = None
    ai_keywords: list[str] = Field(default_factory=list)
    github_url: Url | None = None
    github_stars: int | None = None
    project_url: Url | None = None
    organization: str | None = None
    source_raw: dict | None = None  # Hugging Face 응답 원본 (FR-26)


class HubItem(BaseModel):
    kind: HubKind
    rank: int = Field(ge=1, le=50)
    id: Annotated[str, StringConstraints(pattern=HUB_ID_PATTERN)]
    likes: int = Field(default=0, ge=0)
    downloads: int | None = Field(default=None, ge=0)
    trending_score: float = Field(default=0.0, ge=0)
    task: str | None = None


class PaperDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    what: Para
    novelty: Para
    why: Para
    apply: Para


class GlossaryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    term: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    explanation: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class AnalyzedPaper(BaseModel):
    id: str
    title: str
    authors: list[str]
    abstract: str
    published_at: dt.date | None = None
    upvotes: int
    topic: Topic
    keywords: list[str]
    one_liner: Line
    featured: bool
    detail: PaperDetail | None = None
    glossary: list[GlossaryItem] = Field(default_factory=list, max_length=5)
    github_url: str | None = None
    github_stars: int | None = None
    project_url: str | None = None
    organization: str | None = None
    summary_source: Literal["ai", "hf", "abstract"]
    full_text: str | None = None
    source_raw: dict | None = None


class DigestPayload(BaseModel):
    date: dt.date
    headline: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]] = Field(
        default_factory=list, max_length=3
    )
    provider: str
    papers: list[AnalyzedPaper]
    hub: list[HubItem]


# ---------- AI 응답 형식 (검사용) ----------


class BriefItem(BaseModel):
    id: str
    topic: Topic
    one_liner: Line


class DetailResponse(BaseModel):
    id: str
    topic: Topic
    one_liner: Line
    what: Para
    novelty: Para
    why: Para
    apply: Para
    glossary: list[GlossaryItem] = Field(default_factory=list, max_length=3)


class HeadlineResponse(BaseModel):
    headline: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]] = Field(
        min_length=1, max_length=3
    )


class NarrativeResponse(BaseModel):
    narrative: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]
