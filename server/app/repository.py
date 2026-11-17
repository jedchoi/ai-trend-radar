"""PostgreSQL 저장소 (C-S4). SQL 은 파라미터 바인딩만 사용 (NFR-S06).

- 연결: psycopg 3 + 연결 풀
- 검색: 소문자 검색 문자열 (`search_text`) 에 단어별 부분 일치 (AND), pg_trgm 색인이 있으면 사용
- 날짜 단위 업로드는 한 트랜잭션 (BR-S02)
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager, suppress

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.periods import streak
from app.schemas import (
    Digest,
    DigestIngest,
    DigestSummary,
    HubItem,
    HubItemIn,
    News,
    NewsBrief,
    NewsIngest,
    Paper,
    PaperBrief,
    PaperIn,
)

log = logging.getLogger("radar.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS digests (
    date DATE PRIMARY KEY,
    headline JSONB NOT NULL,
    provider TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    date DATE NOT NULL,
    title TEXT NOT NULL,
    authors JSONB NOT NULL,
    abstract TEXT NOT NULL,
    published_at DATE,
    upvotes INTEGER NOT NULL,
    topic TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    one_liner TEXT NOT NULL,
    featured BOOLEAN NOT NULL,
    detail JSONB,
    glossary JSONB NOT NULL,
    github_url TEXT,
    github_stars INTEGER,
    project_url TEXT,
    organization TEXT,
    summary_source TEXT NOT NULL,
    search_text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(date);
CREATE INDEX IF NOT EXISTS idx_papers_upvotes ON papers(upvotes);
CREATE INDEX IF NOT EXISTS idx_papers_keywords ON papers USING GIN (keywords);
CREATE TABLE IF NOT EXISTS hub_items (
    date DATE NOT NULL,
    kind TEXT NOT NULL,
    item_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    likes INTEGER NOT NULL,
    downloads BIGINT,
    trending_score DOUBLE PRECISION NOT NULL,
    task TEXT,
    PRIMARY KEY (date, kind, item_id)
);
CREATE INDEX IF NOT EXISTS idx_hub_item ON hub_items(kind, item_id, date);
CREATE TABLE IF NOT EXISTS reports (
    period TEXT NOT NULL,
    key TEXT NOT NULL,
    narrative TEXT NOT NULL,
    provider TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (period, key)
);
ALTER TABLE papers ADD COLUMN IF NOT EXISTS full_text TEXT;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS source_raw JSONB;
CREATE TABLE IF NOT EXISTS news (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    organization TEXT,
    authors JSONB NOT NULL,
    image_url TEXT,
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_points JSONB NOT NULL,
    keywords TEXT[] NOT NULL,
    topic TEXT NOT NULL,
    summary_source TEXT NOT NULL,
    provider TEXT NOT NULL,
    source_raw JSONB,
    search_text TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at DESC, id);
CREATE TABLE IF NOT EXISTS ingest_log (
    seq BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    client_ip TEXT NOT NULL,
    count INTEGER NOT NULL
);
"""
# 검색 가속 (선택): 확장을 만들 권한이 없으면 건너뛴다. 없어도 1만 건 규모에서는 NFR-S01 충족
TRGM = [
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE INDEX IF NOT EXISTS idx_papers_search ON papers USING GIN (search_text gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_news_search ON news USING GIN (search_text gin_trgm_ops)",
]
TABLES = ["digests", "papers", "hub_items", "reports", "news", "ingest_log"]

HF_PAPER_URL = "https://huggingface.co/papers/{}"
ARXIV_URL = "https://arxiv.org/abs/{}"
HUB_URL = {
    "model": "https://huggingface.co/{}",
    "dataset": "https://huggingface.co/datasets/{}",
    "space": "https://huggingface.co/spaces/{}",
}
HUB_KIND_ORDER = {"model": 0, "dataset": 1, "space": 2}
SEARCH_MAX_WORDS = 8
SEARCH_MAX_WORD_LEN = 40
_WORD = re.compile(r"\w+", re.UNICODE)


def search_words(q: str | None) -> list[str]:
    """BR-S10: 단어만 남기고 (최대 8개 · 40자) 소문자로. 특수 문자는 버린다."""
    if not q:
        return []
    return [w[:SEARCH_MAX_WORD_LEN].lower() for w in _WORD.findall(q)][:SEARCH_MAX_WORDS]


def like_pattern(word: str) -> str:
    """LIKE 와일드카드 (% _ \\) 를 글자 그대로 취급하도록 이스케이프한 부분 일치 패턴."""
    escaped = word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _search_text(paper: PaperIn) -> str:
    return "\n".join([paper.title, paper.one_liner, paper.abstract, " ".join(paper.keywords)]).lower()


def _insert_paper(conn: psycopg.Connection, day: dt.date, paper: PaperIn) -> None:
    conn.execute(
        """INSERT INTO papers (id, date, title, authors, abstract, published_at, upvotes, topic, keywords, one_liner,
           featured, detail, glossary, github_url, github_stars, project_url, organization, summary_source, search_text,
           full_text, source_raw)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            paper.id,
            day,
            paper.title,
            Jsonb(paper.authors),
            paper.abstract,
            paper.published_at,
            paper.upvotes,
            paper.topic.value,
            paper.keywords,
            paper.one_liner,
            paper.featured,
            Jsonb(paper.detail.model_dump()) if paper.detail else None,
            Jsonb([g.model_dump() for g in paper.glossary]),
            paper.github_url,
            paper.github_stars,
            paper.project_url,
            paper.organization,
            paper.summary_source.value,
            _search_text(paper),
            paper.full_text or None,
            Jsonb(paper.source_raw) if paper.source_raw is not None else None,
        ),
    )


def _insert_hub(conn: psycopg.Connection, day: dt.date, hub: list[HubItemIn]) -> None:
    if not hub:
        return
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO hub_items (date, kind, item_id, rank, likes, downloads, trending_score, task)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            [(day, h.kind, h.id, h.rank, h.likes, h.downloads, h.trending_score, h.task) for h in hub],
        )


def _row_to_paper(row: dict) -> Paper:
    return Paper.model_validate(
        {
            "id": row["id"],
            "date": row["date"],
            "title": row["title"],
            "authors": row["authors"],
            "abstract": row["abstract"],
            "published_at": row["published_at"],
            "upvotes": row["upvotes"],
            "topic": row["topic"],
            "keywords": list(row["keywords"]),
            "one_liner": row["one_liner"],
            "featured": row["featured"],
            "detail": row["detail"],
            "glossary": row["glossary"],
            "github_url": row["github_url"],
            "github_stars": row["github_stars"],
            "project_url": row["project_url"],
            "organization": row["organization"],
            "summary_source": row["summary_source"],
            "hf_url": HF_PAPER_URL.format(row["id"]),
            "arxiv_url": ARXIV_URL.format(row["id"]),
            "full_text": row.get("full_text"),
            "has_full_text": bool(row.get("has_full_text")),
        }
    )


def _row_to_brief(row: dict) -> PaperBrief:
    return PaperBrief(
        id=row["id"],
        title=row["title"],
        date=row["date"],
        topic=row["topic"],
        one_liner=row["one_liner"],
        upvotes=row["upvotes"],
        featured=row["featured"],
        github_url=row["github_url"],
    )


BRIEF_COLUMNS = "p.id, p.title, p.date, p.topic, p.one_liner, p.upvotes, p.featured, p.github_url"
# 일일 요약: 본문 원문 · 원본 JSON 은 빼고 (BR-S31, BR-S32)
DIGEST_PAPER_COLUMNS = (
    "id, date, title, authors, abstract, published_at, upvotes, topic, keywords, one_liner, featured, detail, "
    "glossary, github_url, github_stars, project_url, organization, summary_source, "
    "full_text IS NOT NULL AS has_full_text"
)
DETAIL_PAPER_COLUMNS = DIGEST_PAPER_COLUMNS + ", full_text"
NEWS_BRIEF_COLUMNS = "id, title, url, published_at, organization, image_url, summary, topic, keywords"
NEWS_COLUMNS = NEWS_BRIEF_COLUMNS + ", authors, content, key_points, summary_source, provider"


def ensure_database(url: str) -> None:
    """대상 데이터베이스가 없으면 같은 서버의 postgres 데이터베이스로 접속해 만든다 (기존 Postgres 재사용 시)."""
    info = conninfo_to_dict(url)
    name = info.get("dbname")
    if not name or name == "postgres":
        return
    admin = make_conninfo(url, dbname="postgres")
    with psycopg.connect(admin, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            log.info("created database %s", name)


class Repository:
    def __init__(self, database_url: str, pool_size: int = 5) -> None:
        self.database_url = database_url
        self.pool_size = pool_size
        self.pool: ConnectionPool | None = None

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        if self.pool is None:
            raise RuntimeError("repository not initialised")
        with self.pool.connection() as conn:
            conn.row_factory = dict_row
            yield conn

    def init(self, wait_s: float = 30.0) -> None:
        """DB 가 뜰 때까지 기다린 뒤 (도커 동시 시작) 스키마를 만든다."""
        deadline = time.monotonic() + wait_s
        while True:
            try:
                with suppress(psycopg.Error):  # 권한이 없으면 기존 데이터베이스를 그대로 쓴다
                    ensure_database(self.database_url)
                with psycopg.connect(self.database_url, autocommit=True) as conn:
                    conn.execute(SCHEMA)
                    for stmt in TRGM:
                        try:
                            conn.execute(stmt)
                        except psycopg.Error:
                            log.warning("pg_trgm unavailable; search uses sequential scan")
                            break
                break
            except psycopg.OperationalError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(1)
        # 시각은 UTC 로 주고받는다 (DB 서버의 시간대 설정과 무관하게 같은 응답)
        self.pool = ConnectionPool(
            self.database_url, min_size=1, max_size=self.pool_size, kwargs={"options": "-c TimeZone=UTC"}, open=True
        )

    def close(self) -> None:
        if self.pool is not None:
            self.pool.close()
            self.pool = None

    def reset(self) -> None:
        """모든 데이터 삭제 (테스트 · 예시 데이터 생성용)."""
        with self.connect() as conn:
            conn.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY")  # noqa: S608 - 고정된 테이블 이름

    # ---------- 쓰기 ----------

    def upsert_digest(self, digest: DigestIngest, client_ip: str) -> int:
        """BR-S02 · BR-S03: 날짜 단위 교체를 한 트랜잭션으로."""
        day = digest.date
        ids = [p.id for p in digest.papers]
        with self.connect() as conn, conn.transaction():
            conn.execute("DELETE FROM papers WHERE date = %s OR id = ANY(%s)", (day, ids))
            conn.execute("DELETE FROM hub_items WHERE date = %s", (day,))
            conn.execute(
                """INSERT INTO digests (date, headline, provider, updated_at) VALUES (%s, %s, %s, now())
                   ON CONFLICT (date) DO UPDATE SET headline = EXCLUDED.headline, provider = EXCLUDED.provider,
                   updated_at = now()""",
                (day, Jsonb(digest.headline), digest.provider),
            )
            for paper in digest.papers:
                _insert_paper(conn, day, paper)
            _insert_hub(conn, day, digest.hub)
            conn.execute(
                "INSERT INTO ingest_log (kind, key, client_ip, count) VALUES ('daily', %s, %s, %s)",
                (day.isoformat(), client_ip, len(digest.papers)),
            )
        return len(digest.papers)

    def upsert_report(self, period: str, key: str, narrative: str, provider: str, client_ip: str) -> None:
        with self.connect() as conn, conn.transaction():
            conn.execute(
                """INSERT INTO reports (period, key, narrative, provider, updated_at) VALUES (%s, %s, %s, %s, now())
                   ON CONFLICT (period, key) DO UPDATE SET narrative = EXCLUDED.narrative,
                   provider = EXCLUDED.provider, updated_at = now()""",
                (period, key, narrative, provider),
            )
            conn.execute(
                "INSERT INTO ingest_log (kind, key, client_ip, count) VALUES (%s, %s, %s, 1)",
                (f"report-{period}", key, client_ip),
            )

    def upsert_news(self, news: NewsIngest, client_ip: str) -> int:
        """BR-S30: id 단위 덮어쓰기, 한 트랜잭션."""
        with self.connect() as conn, conn.transaction():
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO news (id, url, title, published_at, organization, authors, image_url, content,
                       summary,
                       key_points, keywords, topic, summary_source, provider, source_raw, search_text, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                       ON CONFLICT (id) DO UPDATE SET url = EXCLUDED.url, title = EXCLUDED.title,
                       published_at = EXCLUDED.published_at, organization = EXCLUDED.organization,
                       authors = EXCLUDED.authors, image_url = EXCLUDED.image_url, content = EXCLUDED.content,
                       summary = EXCLUDED.summary, key_points = EXCLUDED.key_points, keywords = EXCLUDED.keywords,
                       topic = EXCLUDED.topic, summary_source = EXCLUDED.summary_source,
                       provider = EXCLUDED.provider, source_raw = EXCLUDED.source_raw,
                       search_text = EXCLUDED.search_text, updated_at = now()""",
                    [
                        (
                            n.id,
                            n.url,
                            n.title,
                            n.published_at,
                            n.organization,
                            Jsonb(n.authors),
                            n.image_url,
                            n.content,
                            n.summary,
                            Jsonb(n.key_points),
                            n.keywords,
                            n.topic.value,
                            n.summary_source.value,
                            news.provider,
                            Jsonb(n.source_raw) if n.source_raw is not None else None,
                            "\n".join([n.title, n.summary, " ".join(n.keywords), n.content]).lower(),
                        )
                        for n in news.items
                    ],
                )
            conn.execute(
                "INSERT INTO ingest_log (kind, key, client_ip, count) VALUES ('news', %s, %s, %s)",
                (news.items[0].id, client_ip, len(news.items)),
            )
        return len(news.items)

    def list_news(self, q: str | None, topic: str | None, limit: int, offset: int) -> tuple[list[NewsBrief], int]:
        """BR-S33: 최신순, 단어별 부분 일치 (AND)."""
        where: list[str] = []
        params: list = []
        for word in search_words(q):
            where.append("search_text LIKE %s")
            params.append(like_pattern(word))
        if topic:
            where.append("topic = %s")
            params.append(topic)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        with self.connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) AS n FROM news{clause}", params).fetchone()["n"]  # noqa: S608
            rows = conn.execute(
                f"SELECT {NEWS_BRIEF_COLUMNS} FROM news{clause} "  # noqa: S608
                "ORDER BY published_at DESC, id ASC LIMIT %s OFFSET %s",
                [*params, limit, offset],
            ).fetchall()
        return [NewsBrief.model_validate({**r, "keywords": list(r["keywords"])}) for r in rows], total

    def get_news(self, news_id: str) -> News | None:
        with self.connect() as conn:
            row = conn.execute(f"SELECT {NEWS_COLUMNS} FROM news WHERE id = %s", (news_id,)).fetchone()  # noqa: S608
        return News.model_validate({**row, "keywords": list(row["keywords"])}) if row else None

    # ---------- 읽기: 일일 요약 ----------

    def latest_date(self) -> dt.date | None:
        with self.connect() as conn:
            return conn.execute("SELECT MAX(date) AS d FROM digests").fetchone()["d"]

    def digest_dates(self) -> list[dt.date]:
        with self.connect() as conn:
            return [r["date"] for r in conn.execute("SELECT date FROM digests ORDER BY date")]

    def list_digests(self, limit: int) -> list[DigestSummary]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT d.date, d.headline, COUNT(p.id) AS n, COUNT(p.id) FILTER (WHERE p.featured) AS f
                   FROM digests d LEFT JOIN papers p ON p.date = d.date
                   GROUP BY d.date ORDER BY d.date DESC LIMIT %s""",
                (limit,),
            ).fetchall()
        return [
            DigestSummary(date=r["date"], headline=r["headline"], paper_count=r["n"], featured_count=r["f"])
            for r in rows
        ]

    def get_digest(self, day: dt.date) -> Digest | None:
        with self.connect() as conn:
            head = conn.execute("SELECT * FROM digests WHERE date = %s", (day,)).fetchone()
            if head is None:
                return None
            papers = conn.execute(
                f"SELECT {DIGEST_PAPER_COLUMNS} FROM papers WHERE date = %s "  # noqa: S608
                "ORDER BY featured DESC, upvotes DESC, id ASC",
                (day,),
            ).fetchall()
            hub = self._hub_for_day(conn, day)
        return Digest(
            date=day,
            headline=head["headline"],
            provider=head["provider"],
            papers=[_row_to_paper(r) for r in papers],
            hub=hub,
        )

    def _hub_for_day(self, conn: psycopg.Connection, day: dt.date) -> list[HubItem]:
        """BR-S07 (is_new), BR-S08 (streak_days)."""
        rows = conn.execute("SELECT * FROM hub_items WHERE date = %s", (day,)).fetchall()
        if not rows:
            return []
        history = self.hub_presence(conn, until=day)
        prev_day = day - dt.timedelta(days=1)
        kinds_prev_day = {kind for (kind, _), dates in history.items() if prev_day in dates}
        items = []
        for r in rows:
            dates = history[(r["kind"], r["item_id"])]
            items.append(
                HubItem(
                    kind=r["kind"],
                    rank=r["rank"],
                    id=r["item_id"],
                    likes=r["likes"],
                    downloads=r["downloads"],
                    trending_score=r["trending_score"],
                    task=r["task"],
                    is_new=r["kind"] in kinds_prev_day and prev_day not in dates,
                    streak_days=streak(dates, day),
                    url=HUB_URL[r["kind"]].format(r["item_id"]),
                )
            )
        items.sort(key=lambda h: (HUB_KIND_ORDER[h.kind], h.rank, h.id))
        return items

    @staticmethod
    def hub_presence(conn: psycopg.Connection, until: dt.date) -> dict[tuple[str, str], set[dt.date]]:
        """(kind, id) → 등장 날짜 집합."""
        presence: dict[tuple[str, str], set[dt.date]] = defaultdict(set)
        for r in conn.execute("SELECT kind, item_id, date FROM hub_items WHERE date <= %s", (until,)):
            presence[(r["kind"], r["item_id"])].add(r["date"])
        return presence

    # ---------- 읽기: 논문 ----------

    def get_paper(self, paper_id: str) -> Paper | None:
        with self.connect() as conn:
            query = f"SELECT {DETAIL_PAPER_COLUMNS} FROM papers WHERE id = %s"  # noqa: S608
            row = conn.execute(query, (paper_id,)).fetchone()
        return _row_to_paper(row) if row else None

    def related_papers(self, paper: Paper, limit: int = 5) -> list[PaperBrief]:
        """BR-S09."""
        if not paper.keywords:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                f"""SELECT {BRIEF_COLUMNS},
                       cardinality(ARRAY(SELECT unnest(p.keywords) INTERSECT SELECT unnest(%s::text[]))) AS shared
                   FROM papers p
                   WHERE p.keywords && %s::text[] AND p.id <> %s AND p.date <= %s
                   ORDER BY p.date DESC, shared DESC, p.upvotes DESC, p.id ASC LIMIT %s""",  # noqa: S608
                (paper.keywords, paper.keywords, paper.id, paper.date, limit),
            ).fetchall()
        return [_row_to_brief(r) for r in rows]

    def search_papers(
        self,
        q: str | None,
        topic: str | None,
        since: dt.date | None,
        until: dt.date | None,
        featured: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[PaperBrief], int]:
        """BR-S10 · BR-S11."""
        where: list[str] = []
        params: list = []
        for word in search_words(q):
            where.append("p.search_text LIKE %s")
            params.append(like_pattern(word))
        if topic:
            where.append("p.topic = %s")
            params.append(topic)
        if since:
            where.append("p.date >= %s")
            params.append(since)
        if until:
            where.append("p.date <= %s")
            params.append(until)
        if featured is not None:
            where.append("p.featured = %s")
            params.append(featured)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        with self.connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) AS n FROM papers p{clause}", params).fetchone()["n"]  # noqa: S608
            rows = conn.execute(
                f"SELECT {BRIEF_COLUMNS} FROM papers p{clause} "  # noqa: S608
                "ORDER BY p.date DESC, p.upvotes DESC, p.id ASC LIMIT %s OFFSET %s",
                [*params, limit, offset],
            ).fetchall()
        return [_row_to_brief(r) for r in rows], total

    # ---------- 읽기: 통계용 ----------

    def topic_counts(self, start: dt.date, end: dt.date) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT topic, COUNT(*) AS n FROM papers WHERE date BETWEEN %s AND %s GROUP BY topic", (start, end)
            ).fetchall()
        return {r["topic"]: r["n"] for r in rows}

    def keyword_counts(self, start: dt.date, end: dt.date) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT k AS keyword, COUNT(*) AS n FROM papers p, unnest(p.keywords) AS k
                   WHERE p.date BETWEEN %s AND %s GROUP BY k""",
                (start, end),
            ).fetchall()
        return {r["keyword"]: r["n"] for r in rows}

    def paper_count(self, start: dt.date, end: dt.date) -> int:
        with self.connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) AS n FROM papers WHERE date BETWEEN %s AND %s", (start, end)
            ).fetchone()["n"]

    def has_digest_between(self, start: dt.date, end: dt.date) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT 1 FROM digests WHERE date BETWEEN %s AND %s LIMIT 1", (start, end)).fetchone()
        return row is not None

    def top_papers(self, start: dt.date, end: dt.date, limit: int = 5) -> list[PaperBrief]:
        with self.connect() as conn:
            rows = conn.execute(
                f"""SELECT {BRIEF_COLUMNS} FROM papers p WHERE p.date BETWEEN %s AND %s
                   ORDER BY p.upvotes DESC, p.date DESC, p.id ASC LIMIT %s""",  # noqa: S608
                (start, end, limit),
            ).fetchall()
        return [_row_to_brief(r) for r in rows]

    def hub_history(self, until: dt.date) -> dict[tuple[str, str], set[dt.date]]:
        with self.connect() as conn:
            return self.hub_presence(conn, until=until)

    def get_report(self, period: str, key: str) -> tuple[str, str] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT narrative, provider FROM reports WHERE period = %s AND key = %s", (period, key)
            ).fetchone()
        return (row["narrative"], row["provider"]) if row else None
