"""SQLite 저장소 (C-S4). SQL 은 파라미터 바인딩만 사용 (NFR-S06)."""

from __future__ import annotations

import datetime as dt
import json
import re
import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager

from app.periods import streak
from app.schemas import (
    Digest,
    DigestIngest,
    DigestSummary,
    HubItem,
    HubItemIn,
    Paper,
    PaperBrief,
    PaperIn,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS digests (
    date TEXT PRIMARY KEY,
    headline_json TEXT NOT NULL,
    provider TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    title TEXT NOT NULL,
    authors_json TEXT NOT NULL,
    abstract TEXT NOT NULL,
    published_at TEXT,
    upvotes INTEGER NOT NULL,
    topic TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    one_liner TEXT NOT NULL,
    featured INTEGER NOT NULL,
    detail_json TEXT,
    glossary_json TEXT NOT NULL,
    github_url TEXT,
    github_stars INTEGER,
    project_url TEXT,
    organization TEXT,
    summary_source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(date);
CREATE INDEX IF NOT EXISTS idx_papers_upvotes ON papers(upvotes);
CREATE TABLE IF NOT EXISTS paper_keywords (
    paper_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    PRIMARY KEY (paper_id, keyword)
);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON paper_keywords(keyword);
CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(title, one_liner, abstract, keywords);
CREATE TABLE IF NOT EXISTS hub_items (
    date TEXT NOT NULL,
    kind TEXT NOT NULL,
    item_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    likes INTEGER NOT NULL,
    downloads INTEGER,
    trending_score REAL NOT NULL,
    task TEXT,
    PRIMARY KEY (date, kind, item_id)
);
CREATE INDEX IF NOT EXISTS idx_hub_item ON hub_items(kind, item_id, date);
CREATE TABLE IF NOT EXISTS reports (
    period TEXT NOT NULL,
    key TEXT NOT NULL,
    narrative TEXT NOT NULL,
    provider TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (period, key)
);
CREATE TABLE IF NOT EXISTS ingest_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    client_ip TEXT NOT NULL,
    count INTEGER NOT NULL
);
"""

HF_PAPER_URL = "https://huggingface.co/papers/{}"
HUB_URL = {
    "model": "https://huggingface.co/{}",
    "dataset": "https://huggingface.co/datasets/{}",
    "space": "https://huggingface.co/spaces/{}",
}
HUB_KIND_ORDER = {"model": 0, "dataset": 1, "space": 2}
SEARCH_MAX_WORDS = 8
SEARCH_MAX_WORD_LEN = 40
_WORD = re.compile(r"\w+", re.UNICODE)


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def fts_query(q: str | None) -> str | None:
    """BR-S10: 단어만 남기고 (최대 8개 · 40자) 접두어 AND 질의로 만든다. 단어가 없으면 None."""
    if not q:
        return None
    words = [w[:SEARCH_MAX_WORD_LEN] for w in _WORD.findall(q)][:SEARCH_MAX_WORDS]
    if not words:
        return None
    return " AND ".join(f'"{w}"*' for w in words)


def _insert_paper(conn: sqlite3.Connection, day: dt.date, paper: PaperIn) -> None:
    cur = conn.execute(
        """INSERT INTO papers (id, date, title, authors_json, abstract, published_at, upvotes, topic,
           keywords_json, one_liner, featured, detail_json, glossary_json, github_url, github_stars,
           project_url, organization, summary_source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            paper.id,
            day.isoformat(),
            paper.title,
            json.dumps(paper.authors, ensure_ascii=False),
            paper.abstract,
            paper.published_at.isoformat() if paper.published_at else None,
            paper.upvotes,
            paper.topic.value,
            json.dumps(paper.keywords, ensure_ascii=False),
            paper.one_liner,
            int(paper.featured),
            paper.detail.model_dump_json() if paper.detail else None,
            json.dumps([g.model_dump() for g in paper.glossary], ensure_ascii=False),
            paper.github_url,
            paper.github_stars,
            paper.project_url,
            paper.organization,
            paper.summary_source.value,
        ),
    )
    conn.execute(
        "INSERT INTO papers_fts (rowid, title, one_liner, abstract, keywords) VALUES (?, ?, ?, ?, ?)",
        (cur.lastrowid, paper.title, paper.one_liner, paper.abstract, " ".join(paper.keywords)),
    )
    conn.executemany(
        "INSERT INTO paper_keywords (paper_id, keyword) VALUES (?, ?)",
        [(paper.id, k) for k in paper.keywords],
    )


def _insert_hub(conn: sqlite3.Connection, day: dt.date, hub: list[HubItemIn]) -> None:
    conn.executemany(
        """INSERT INTO hub_items (date, kind, item_id, rank, likes, downloads, trending_score, task)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [(day.isoformat(), h.kind, h.id, h.rank, h.likes, h.downloads, h.trending_score, h.task) for h in hub],
    )


def _row_to_paper(row: sqlite3.Row) -> Paper:
    return Paper.model_validate(
        {
            "id": row["id"],
            "date": row["date"],
            "title": row["title"],
            "authors": json.loads(row["authors_json"]),
            "abstract": row["abstract"],
            "published_at": row["published_at"],
            "upvotes": row["upvotes"],
            "topic": row["topic"],
            "keywords": json.loads(row["keywords_json"]),
            "one_liner": row["one_liner"],
            "featured": bool(row["featured"]),
            "detail": json.loads(row["detail_json"]) if row["detail_json"] else None,
            "glossary": json.loads(row["glossary_json"]),
            "github_url": row["github_url"],
            "github_stars": row["github_stars"],
            "project_url": row["project_url"],
            "organization": row["organization"],
            "summary_source": row["summary_source"],
            "hf_url": HF_PAPER_URL.format(row["id"]),
        }
    )


def _row_to_brief(row: sqlite3.Row) -> PaperBrief:
    return PaperBrief(
        id=row["id"],
        title=row["title"],
        date=row["date"],
        topic=row["topic"],
        one_liner=row["one_liner"],
        upvotes=row["upvotes"],
        featured=bool(row["featured"]),
        github_url=row["github_url"],
    )


class Repository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)

    # ---------- 쓰기 ----------

    def upsert_digest(self, digest: DigestIngest, client_ip: str) -> int:
        """BR-S02 · BR-S03: 날짜 단위 교체를 한 트랜잭션으로."""
        day = digest.date.isoformat()
        ids = [p.id for p in digest.papers]
        with self.connect() as conn, conn:
            stale = "SELECT rowid FROM papers WHERE date = ? OR id IN (SELECT value FROM json_each(?))"
            params = (day, json.dumps(ids))
            conn.execute(f"DELETE FROM papers_fts WHERE rowid IN ({stale})", params)  # noqa: S608
            conn.execute(
                "DELETE FROM paper_keywords WHERE paper_id IN "
                "(SELECT id FROM papers WHERE date = ? OR id IN (SELECT value FROM json_each(?)))",
                params,
            )
            conn.execute("DELETE FROM papers WHERE date = ? OR id IN (SELECT value FROM json_each(?))", params)
            conn.execute("DELETE FROM hub_items WHERE date = ?", (day,))
            conn.execute(
                """INSERT INTO digests (date, headline_json, provider, updated_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT(date) DO UPDATE SET headline_json = excluded.headline_json,
                   provider = excluded.provider, updated_at = excluded.updated_at""",
                (day, json.dumps(digest.headline, ensure_ascii=False), digest.provider, _now()),
            )
            for paper in digest.papers:
                _insert_paper(conn, digest.date, paper)
            _insert_hub(conn, digest.date, digest.hub)
            conn.execute(
                "INSERT INTO ingest_log (ts, kind, key, client_ip, count) VALUES (?, 'daily', ?, ?, ?)",
                (_now(), day, client_ip, len(digest.papers)),
            )
        return len(digest.papers)

    def upsert_report(self, period: str, key: str, narrative: str, provider: str, client_ip: str) -> None:
        with self.connect() as conn, conn:
            conn.execute(
                """INSERT INTO reports (period, key, narrative, provider, updated_at) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(period, key) DO UPDATE SET narrative = excluded.narrative,
                   provider = excluded.provider, updated_at = excluded.updated_at""",
                (period, key, narrative, provider, _now()),
            )
            conn.execute(
                "INSERT INTO ingest_log (ts, kind, key, client_ip, count) VALUES (?, ?, ?, ?, 1)",
                (_now(), f"report-{period}", key, client_ip),
            )

    # ---------- 읽기: 일일 요약 ----------

    def latest_date(self) -> dt.date | None:
        with self.connect() as conn:
            row = conn.execute("SELECT MAX(date) AS d FROM digests").fetchone()
        return dt.date.fromisoformat(row["d"]) if row["d"] else None

    def digest_dates(self) -> list[dt.date]:
        with self.connect() as conn:
            rows = conn.execute("SELECT date FROM digests ORDER BY date").fetchall()
        return [dt.date.fromisoformat(r["date"]) for r in rows]

    def list_digests(self, limit: int) -> list[DigestSummary]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT d.date, d.headline_json, COUNT(p.id) AS n, COALESCE(SUM(p.featured), 0) AS f
                   FROM digests d LEFT JOIN papers p ON p.date = d.date
                   GROUP BY d.date ORDER BY d.date DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [
            DigestSummary(
                date=r["date"], headline=json.loads(r["headline_json"]), paper_count=r["n"], featured_count=r["f"]
            )
            for r in rows
        ]

    def get_digest(self, day: dt.date) -> Digest | None:
        with self.connect() as conn:
            head = conn.execute("SELECT * FROM digests WHERE date = ?", (day.isoformat(),)).fetchone()
            if head is None:
                return None
            papers = conn.execute(
                "SELECT * FROM papers WHERE date = ? ORDER BY featured DESC, upvotes DESC, id ASC",
                (day.isoformat(),),
            ).fetchall()
            hub = self._hub_for_day(conn, day)
        return Digest(
            date=day,
            headline=json.loads(head["headline_json"]),
            provider=head["provider"],
            papers=[_row_to_paper(r) for r in papers],
            hub=hub,
        )

    def _hub_for_day(self, conn: sqlite3.Connection, day: dt.date) -> list[HubItem]:
        """BR-S07 (is_new), BR-S08 (streak_days)."""
        rows = conn.execute("SELECT * FROM hub_items WHERE date = ?", (day.isoformat(),)).fetchall()
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
    def hub_presence(
        conn: sqlite3.Connection, until: dt.date, since: dt.date | None = None
    ) -> dict[tuple[str, str], set[dt.date]]:
        """(kind, id) → 등장 날짜 집합."""
        params: list[str] = [until.isoformat()]
        sql = "SELECT kind, item_id, date FROM hub_items WHERE date <= ?"
        if since is not None:
            sql += " AND date >= ?"
            params.append(since.isoformat())
        presence: dict[tuple[str, str], set[dt.date]] = defaultdict(set)
        for r in conn.execute(sql, params):
            presence[(r["kind"], r["item_id"])].add(dt.date.fromisoformat(r["date"]))
        return presence

    # ---------- 읽기: 논문 ----------

    def get_paper(self, paper_id: str) -> Paper | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
        return _row_to_paper(row) if row else None

    def related_papers(self, paper: Paper, limit: int = 5) -> list[PaperBrief]:
        """BR-S09."""
        if not paper.keywords:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT p.*, COUNT(*) AS shared FROM paper_keywords k JOIN papers p ON p.id = k.paper_id
                   WHERE k.keyword IN (SELECT value FROM json_each(?)) AND p.id != ? AND p.date <= ?
                   GROUP BY p.id ORDER BY p.date DESC, shared DESC, p.upvotes DESC, p.id ASC LIMIT ?""",
                (json.dumps(paper.keywords), paper.id, paper.date.isoformat(), limit),
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
        joins, where, params = "", [], []
        match = fts_query(q)
        if match:
            joins = " JOIN papers_fts f ON f.rowid = p.rowid"
            where.append("papers_fts MATCH ?")
            params.append(match)
        if topic:
            where.append("p.topic = ?")
            params.append(topic)
        if since:
            where.append("p.date >= ?")
            params.append(since.isoformat())
        if until:
            where.append("p.date <= ?")
            params.append(until.isoformat())
        if featured is not None:
            where.append("p.featured = ?")
            params.append(int(featured))
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        base = f"FROM papers p{joins}{clause}"
        with self.connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) AS n {base}", params).fetchone()["n"]  # noqa: S608
            rows = conn.execute(
                f"SELECT p.* {base} ORDER BY p.date DESC, p.upvotes DESC, p.id ASC LIMIT ? OFFSET ?",  # noqa: S608
                [*params, limit, offset],
            ).fetchall()
        return [_row_to_brief(r) for r in rows], total

    # ---------- 읽기: 통계용 ----------

    def topic_counts(self, start: dt.date, end: dt.date) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT topic, COUNT(*) AS n FROM papers WHERE date BETWEEN ? AND ? GROUP BY topic",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return {r["topic"]: r["n"] for r in rows}

    def keyword_counts(self, start: dt.date, end: dt.date) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT k.keyword, COUNT(*) AS n FROM paper_keywords k JOIN papers p ON p.id = k.paper_id
                   WHERE p.date BETWEEN ? AND ? GROUP BY k.keyword""",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return {r["keyword"]: r["n"] for r in rows}

    def paper_count(self, start: dt.date, end: dt.date) -> int:
        with self.connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) AS n FROM papers WHERE date BETWEEN ? AND ?", (start.isoformat(), end.isoformat())
            ).fetchone()["n"]

    def has_digest_between(self, start: dt.date, end: dt.date) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM digests WHERE date BETWEEN ? AND ? LIMIT 1", (start.isoformat(), end.isoformat())
            ).fetchone()
        return row is not None

    def top_papers(self, start: dt.date, end: dt.date, limit: int = 5) -> list[PaperBrief]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT * FROM papers WHERE date BETWEEN ? AND ?
                   ORDER BY upvotes DESC, date DESC, id ASC LIMIT ?""",
                (start.isoformat(), end.isoformat(), limit),
            ).fetchall()
        return [_row_to_brief(r) for r in rows]

    def hub_history(self, until: dt.date) -> dict[tuple[str, str], set[dt.date]]:
        with self.connect() as conn:
            return self.hub_presence(conn, until=until)

    def get_report(self, period: str, key: str) -> tuple[str, str] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT narrative, provider FROM reports WHERE period = ? AND key = ?", (period, key)
            ).fetchone()
        return (row["narrative"], row["provider"]) if row else None
