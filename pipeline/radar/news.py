"""Hugging Face 블로그 뉴스 (FR-25, BR-P30 ~ BR-P33): RSS → 본문 원문 → 분석.

- RSS: https://huggingface.co/blog/feed.xml (title · pubDate · link · guid, 본문 없음)
- 본문: 글 페이지 HTML 에서 `blog-content` → `article` → `main` 순으로 찾아 텍스트로 바꾼다
- 같은 호스트 (huggingface.co) 의 /blog/ 주소만 가져온다
"""

from __future__ import annotations

import datetime as dt
import email.utils
import json
import re
import xml.etree.ElementTree as ET  # noqa: S405 - DOCTYPE/ENTITY 가 있으면 파싱하지 않는다 (parse_feed)
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from radar.models import Topic
from radar.topics import classify

FEED_PATH = "/blog/feed.xml"
BLOG_HOST = "huggingface.co"
CONTENT_MAX = 200_000
SUMMARY_MAX = 800
POINT_MAX = 300
MAX_POINTS = 5
FALLBACK_SUMMARY_CHARS = 300
_ID_PART = re.compile(r"[^a-z0-9._-]+")


@dataclass
class FeedItem:
    id: str
    url: str
    title: str
    published_at: dt.datetime
    raw: dict


@dataclass
class Article:
    content: str = ""
    headings: list[str] = field(default_factory=list)
    image_url: str | None = None
    authors: list[str] = field(default_factory=list)


class NewsPayloadItem(BaseModel):
    """서버 계약 NewsIn 과 같은 필드 (tests/test_contract.py 가 서버 스키마로 검사)."""

    id: str
    url: str
    title: str
    published_at: dt.datetime
    organization: str | None = None
    authors: list[str] = Field(default_factory=list)
    image_url: str | None = None
    content: str = ""
    summary: str
    key_points: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    topic: Topic = Topic.OTHER
    summary_source: Literal["ai", "abstract"] = "abstract"
    source_raw: dict | None = None


class NewsResponse(BaseModel):
    """AI 응답 형식 (prompts/news.md)."""

    topic: Topic
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=SUMMARY_MAX)]
    key_points: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=POINT_MAX)]] = (
        Field(default_factory=list, max_length=6)
    )
    keywords: list[str] = Field(default_factory=list, max_length=15)


# ---------- RSS ----------


def news_id(url: str) -> str | None:
    """https://huggingface.co/blog/ggml-org/llama-cpp-v1 → ggml-org/llama-cpp-v1 (블로그 주소가 아니면 None)."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != BLOG_HOST or not parsed.path.startswith("/blog/"):
        return None
    parts = [p for p in parsed.path[len("/blog/") :].lower().split("/") if p]
    if not parts or len(parts) > 2:
        return None
    parts = [_ID_PART.sub("-", p).strip("-._")[:150] for p in parts]
    if not all(parts):
        return None
    parts[0] = parts[0][:100]
    return "/".join(parts)


def parse_feed(xml_text: str) -> list[FeedItem]:
    """RSS 2.0 → FeedItem (최신순 그대로). 형식이 틀린 항목은 건너뛴다."""
    head = xml_text[:2000].upper()
    if "<!DOCTYPE" in head or "<!ENTITY" in xml_text.upper():
        raise ValueError("feed: DOCTYPE/ENTITY 는 허용하지 않음")
    root = ET.fromstring(xml_text)  # noqa: S314 - 위에서 엔티티 선언을 막았다
    items: list[FeedItem] = []
    for node in root.iter("item"):
        raw = {child.tag: (child.text or "").strip() for child in node}
        url = raw.get("link") or raw.get("guid") or ""
        nid = news_id(url)
        title = raw.get("title", "")
        try:
            published = email.utils.parsedate_to_datetime(raw.get("pubDate", ""))
        except (TypeError, ValueError):
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=dt.UTC)
        if nid and title:
            items.append(FeedItem(nid, url, title[:500], published.astimezone(dt.UTC), raw))
    return items


# ---------- 본문 추출 ----------

SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript", "svg", "form", "button", "iframe"}
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "pre", "blockquote", "td", "th", "figcaption", "dd", "dt"}
HEADING_TAGS = {"h2", "h3"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _Extractor(HTMLParser):
    """블록 단위 텍스트. 루트 후보: class 에 blog-content 가 있는 요소 > article > main > body."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []  # (tag, 루트 종류)
        self.skip = 0
        self.blocks: dict[str, list[tuple[str, str]]] = {"blog": [], "article": [], "main": [], "body": []}
        self.current: list[str] = []
        self.current_tag: str | None = None
        self.og_image: str | None = None
        self.authors: list[str] = []

    def _roots(self) -> set[str]:
        return {kind for _, kind in self.stack if kind} | {"body"}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v or "" for k, v in attrs}
        if tag == "meta":
            if attr.get("property") == "og:image" and attr.get("content", "").startswith("https://"):
                self.og_image = attr["content"][:500]
            if attr.get("name") == "author" and attr.get("content"):
                self.authors.append(attr["content"][:200])
            return
        if tag in VOID_TAGS:
            if tag == "br":
                self.current.append("\n")
            return
        kind = None
        classes = attr.get("class", "").split()
        if any(c.startswith("blog-content") for c in classes):
            kind = "blog"
        elif tag in ("article", "main"):
            kind = tag
        self.stack.append((tag, kind))
        if tag in SKIP_TAGS:
            self.skip += 1
        elif tag in BLOCK_TAGS and not self.skip:
            self._flush()
            self.current_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        if tag in BLOCK_TAGS and not self.skip:
            self._flush()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for closed, _ in self.stack[i:]:
                    if closed in SKIP_TAGS:
                        self.skip = max(0, self.skip - 1)
                del self.stack[i:]
                break

    def handle_data(self, data: str) -> None:
        if not self.skip and self.current_tag:
            self.current.append(data)

    def _flush(self) -> None:
        if self.current_tag is None:
            return
        tag = self.current_tag
        text = "".join(self.current)
        text = text.strip("\n") if tag == "pre" else " ".join(text.split())
        self.current, self.current_tag = [], None
        if text:
            for root in self._roots():
                self.blocks[root].append((tag, text))

    def result(self) -> Article:
        self._flush()
        for root in ("blog", "article", "main", "body"):
            blocks = self.blocks[root]
            if sum(len(t) for _, t in blocks) >= 200 or (root == "body" and blocks):
                break
        lines = []
        for tag, text in blocks:
            if tag in ("h1", "h2", "h3", "h4"):
                lines.append(f"\n## {text}")
            elif tag == "li":
                lines.append(f"- {text}")
            else:
                lines.append(text)
        content = unescape("\n".join(lines)).strip()[:CONTENT_MAX]
        headings = [t for tag, t in blocks if tag in HEADING_TAGS][:20]
        return Article(content=content, headings=headings, image_url=self.og_image, authors=self.authors[:30])


def extract_article(html: str) -> Article:
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    return parser.result()


# ---------- 분석 ----------


def _first_paragraph(content: str) -> str:
    for block in content.split("\n"):
        block = block.strip()
        if len(block) >= 40 and not block.startswith(("##", "- ")):
            return block
    return content.strip()


def fallback_news(item: FeedItem, article: Article) -> NewsPayloadItem:
    """BR-P32: AI 없이 = 첫 문단 요약 · 소제목 핵심 · 규칙 분류."""
    first = _first_paragraph(article.content) or item.title
    summary = first if len(first) <= FALLBACK_SUMMARY_CHARS else first[:FALLBACK_SUMMARY_CHARS].rstrip() + "…"
    topic = classify(item.title, [], article.content[:3000])
    return _payload(item, article, summary, [h[:POINT_MAX] for h in article.headings[:MAX_POINTS]], [], topic, False)


def _payload(item, article, summary, points, keywords, topic, ai: bool) -> NewsPayloadItem:
    org = item.id.split("/")[0] if "/" in item.id else None
    return NewsPayloadItem(
        id=item.id,
        url=item.url,
        title=item.title,
        published_at=item.published_at,
        organization=org,
        authors=article.authors,
        image_url=article.image_url,
        content=article.content,
        summary=summary[:SUMMARY_MAX],
        key_points=points[:MAX_POINTS],
        keywords=keywords,
        topic=topic,
        summary_source="ai" if ai else "abstract",
        source_raw=item.raw,
    )


def analyze_news(analyzer, item: FeedItem, article: Article, text_chars: int = 20000) -> tuple[NewsPayloadItem, bool]:
    """(결과, AI 대체 여부). AI 가 없거나 형식이 계속 틀리면 규칙 결과."""
    from radar.analyze import normalize_keywords

    if analyzer.provider is None or not article.content:
        return fallback_news(item, article), analyzer.provider is not None
    got = analyzer._ask_model(
        "news",
        {"TITLE": item.title, "URL": item.url, "TEXT": article.content[:text_chars]},
        NewsResponse,
    )
    if got is None:
        return fallback_news(item, article), True
    keywords = normalize_keywords(got.keywords)
    return _payload(item, article, got.summary, got.key_points, keywords, got.topic, True), False


def to_json(items: list[NewsPayloadItem]) -> list[dict]:
    return [json.loads(i.model_dump_json()) for i in items]


__all__ = [
    "Article",
    "FeedItem",
    "NewsPayloadItem",
    "NewsResponse",
    "ValidationError",
    "analyze_news",
    "extract_article",
    "fallback_news",
    "news_id",
    "parse_feed",
]
