"""번역 (C-P10, FR-34 ~ FR-36, BR-P40 ~ BR-P45): 서버의 원본을 읽어 반대 언어 번역을 만들어 미리 올린다.

- 한국어로: 논문 제목, 뉴스 제목 · 본문 원문 (논문 원문 = 초록 · 본문은 영어 그대로, FR-34 개정 2026-11-18)
- 영어로: 한 줄 요약 · 상세 요약 · 용어 · 오늘의 세 줄 · 뉴스 요약 · 핵심 · 리포트 문장
- 순서: 짧은 항목 (최근 날부터) → 긴 본문 (최근 것부터). 같은 원본은 한 번만 (해시), 바뀌면 다시
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from radar.analyze import RETRY_NOTE, extract_json, fill, load_prompt, split_prompt

LANG_NAMES = {"ko": "Korean (한국어)", "en": "English"}
PAPER_BATCH = 5  # 논문 요약 (영어로)
PAPER_TITLE_BATCH = 10  # 논문 제목 (한국어로)
NEWS_TITLE_BATCH = 10
UPLOAD_BATCH = 20
UPLOAD_MAX_CHARS = 3_000_000  # 업로드 한 번 (서버 한도 10 MB, 한글 3바이트)
MIN_RATIO = 0.15  # 긴 글 조각: 번역이 원문 길이의 15% 미만이면 실패 (NFR-14)
_FENCED = re.compile(r"^```[a-zA-Z]*\n(.*)\n```$", re.DOTALL)


class StopTranslating(Exception):
    """시간 상한 (BR-P44)."""


@dataclass
class Job:
    kind: str  # paper · news · digest · report
    key: str
    lang: str
    part: str  # short · full
    source: dict

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.key}:{self.lang}:{self.part}"

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.source, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def same_shape(source: Any, result: Any) -> bool:
    """BR-P42: 같은 키 · 같은 길이 · 빈 문자열 없음."""
    if isinstance(source, dict):
        return (
            isinstance(result, dict)
            and set(source) == set(result)
            and all(same_shape(source[k], result[k]) for k in source)
        )
    if isinstance(source, list):
        return (
            isinstance(result, list)
            and len(source) == len(result)
            and all(same_shape(a, b) for a, b in zip(source, result, strict=True))
        )
    if isinstance(source, str):
        return isinstance(result, str) and bool(result.strip())
    return source == result


def split_text(text: str, limit: int) -> list[str]:
    """문단 (빈 줄) 경계로 limit 자 안팎씩. 문단 하나가 길면 줄 → 문장 → 글자 수로 자른다."""
    pieces: list[str] = []
    for para in text.split("\n\n"):
        while len(para) > limit:
            cut = para.rfind("\n", 0, limit)
            if cut < limit // 2:
                cut = max(para.rfind(". ", 0, limit), para.rfind("。", 0, limit))
                cut = cut + 1 if cut >= limit // 2 else limit
            pieces.append(para[:cut])
            para = para[cut:].lstrip("\n")
        pieces.append(para)
    chunks: list[str] = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + 2 + len(piece) <= limit:
            chunks[-1] += "\n\n" + piece
        else:
            chunks.append(piece)
    return [c for c in chunks if c.strip()] or ([text] if text.strip() else [])


def _strip_fence(text: str) -> str:
    text = text.strip()
    match = _FENCED.match(text)
    return match.group(1).strip() if match else text


class Translator:
    def __init__(
        self,
        provider,
        server,
        state_path,
        chunk_chars: int = 6000,
        full_text: bool = True,
        max_minutes: int = 180,
        clock: Callable[[], float] = time.monotonic,
        log: Callable[[str], None] = print,
    ) -> None:
        self.provider = provider
        self.server = server
        self.state_path = state_path
        self.chunk_chars = chunk_chars
        self.full_text = full_text
        self.max_minutes = max_minutes
        self.clock = clock
        self.log = log
        self.state = self._load_state()
        self.pending: list[tuple[Job, dict]] = []
        self.done = 0
        self.failed = 0
        self.deadline: float | None = None

    # ---------- 상태 (BR-P43) ----------

    def _load_state(self) -> dict:
        if self.state_path is None:  # 저장하지 않음 (시험용)
            return {}
        try:
            return json.loads(self.state_path.read_text())
        except (FileNotFoundError, ValueError):
            return {}

    def _save_state(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, sort_keys=True))

    def needed(self, job: Job) -> bool:
        return self.state.get(job.id, {}).get("h") != job.digest

    # ---------- AI 호출 ----------

    def _check_time(self) -> None:
        if self.deadline is not None and self.clock() > self.deadline:
            raise StopTranslating

    def _ask_json(self, lang: str, data: dict) -> Any:
        self._check_time()
        system, user = split_prompt(load_prompt("translate"))
        values = {"LANG": LANG_NAMES[lang], "JSON": json.dumps(data, ensure_ascii=False)}
        last: Any = None
        for attempt in range(2):
            try:
                text = self.provider.complete(
                    fill(system, **values), (RETRY_NOTE if attempt else "") + fill(user, **values)
                )
                last = extract_json(text)
            except Exception:  # noqa: BLE001, S112 - 제공자 오류 · 형식 위반은 재요청 대상 (BR-P42)
                continue
            if isinstance(last, dict):
                return last
        return last

    def translate_object(self, lang: str, data: dict) -> dict | None:
        """dict 하나 (키 구조 유지) 번역. 형식이 맞지 않으면 1회 재요청 후 None."""
        for _ in range(2):
            got = self._ask_json(lang, data)
            if same_shape(data, got):
                return got
        return None

    def translate_batch(self, lang: str, items: dict[str, dict]) -> dict[str, dict]:
        """{id: 필드} 묶음. 맞게 돌아온 id 만, 빠진 id 는 1회 더 묻는다."""
        result: dict[str, dict] = {}
        todo = dict(items)
        for _ in range(2):
            if not todo:
                break
            got = self._ask_json(lang, todo)
            if isinstance(got, dict):
                for key, value in got.items():
                    if key in todo and same_shape(todo[key], value):
                        result[key] = value
                        todo.pop(key)
        return result

    def translate_text(self, lang: str, text: str) -> str | None:
        """긴 글: 조각마다 번역해 이어 붙인다. 한 조각이라도 실패하면 None (다음 실행에서 다시)."""
        system, user = split_prompt(load_prompt("translate_text"))
        out: list[str] = []
        for chunk in split_text(text, self.chunk_chars):
            done = None
            for attempt in range(2):
                self._check_time()
                values = {"LANG": LANG_NAMES[lang], "TEXT": chunk}
                try:
                    got = _strip_fence(
                        self.provider.complete(
                            fill(system, **values), (RETRY_NOTE if attempt else "") + fill(user, **values)
                        )
                    )
                except Exception:  # noqa: BLE001, S112
                    continue
                if got and len(got) >= MIN_RATIO * len(chunk):
                    done = got
                    break
            if done is None:
                return None
            out.append(done)
        return "\n\n".join(out)

    # ---------- 업로드 ----------

    def _add(self, job: Job, fields: dict) -> None:
        self.pending.append((job, fields))
        size = sum(len(json.dumps(f, ensure_ascii=False)) for _, f in self.pending)
        if len(self.pending) >= UPLOAD_BATCH or size > UPLOAD_MAX_CHARS:
            self.flush()

    def flush(self) -> None:
        if not self.pending:
            return
        items = [{"kind": j.kind, "key": j.key, "lang": j.lang, "fields": f} for j, f in self.pending]
        self.server.upload_translations(items, self.provider.name)
        for job, _ in self.pending:
            self.state[job.id] = {"h": job.digest, "p": self.provider.name}
        self.done += len(self.pending)
        self.pending = []
        self._save_state()

    # ---------- 대상 모으기 ----------

    def _digest_jobs(self, digest: dict) -> tuple[list[Job], list[Job]]:
        day = digest["date"]
        short: list[Job] = []
        if digest.get("headline"):
            short.append(Job("digest", day, "en", "short", {"headline": digest["headline"]}))
        for p in digest.get("papers", []):
            short.append(Job("paper", p["id"], "ko", "short", {"title": p["title"]}))
            en: dict = {"one_liner": p["one_liner"]}
            if p.get("detail"):
                en["detail"] = p["detail"]
            if p.get("glossary"):
                en["glossary"] = p["glossary"]
            short.append(Job("paper", p["id"], "en", "short", en))
        return short, []

    def _news_jobs(self, news: dict) -> tuple[list[Job], list[Job]]:
        short = [
            Job("news", news["id"], "ko", "short", {"title": news["title"]}),
            Job(
                "news",
                news["id"],
                "en",
                "short",
                {"summary": news["summary"], **({"key_points": news["key_points"]} if news.get("key_points") else {})},
            ),
        ]
        full = [Job("news", news["id"], "ko", "full", {"content": news["content"]})] if news.get("content") else []
        return short, full

    # ---------- 실행 ----------

    def run(self, days: int, today: dt.date) -> dict:
        """BR-P40: 짧은 항목 → 긴 본문. 결과 요약을 돌려준다."""
        started = self.clock()
        self.deadline = started + self.max_minutes * 60 if self.max_minutes > 0 else None
        stopped = False
        try:
            short, full = self._collect(days, today)
            self.log(f"번역 대상: 짧은 항목 {len(short)}건, 긴 본문 {len(full)}건 (이미 된 것 제외)")
            self._run_short(short)
            self.flush()
            if self.full_text:
                self._run_full(full)
            self.flush()
        except StopTranslating:
            self.flush()
            stopped = True
            self.log(f"번역 시간 상한 ({self.max_minutes}분) 에 걸려 멈춤. 다음 실행에서 이어서 합니다")
        return {"done": self.done, "failed": self.failed, "stopped": stopped}

    def _collect(self, days: int, today: dt.date) -> tuple[list[Job], list[Job]]:
        cutoff = today - dt.timedelta(days=days)
        short: list[Job] = []
        full: list[Job] = []
        dates = [d["date"] for d in self.server.get_json("/api/v1/digests", {"limit": 90}).get("items", [])]
        for day in dates:  # 최신순
            if dt.date.fromisoformat(day) < cutoff:
                continue
            s, f = self._digest_jobs(self.server.get_json(f"/api/v1/digests/{day}"))
            short += s
            full += f
        news_short, news_full = [], []
        for brief in self._recent_news(cutoff):
            s, f = self._news_jobs(self.server.get_json(f"/api/v1/news/{brief['id']}"))
            news_short += s
            news_full += f
        report_jobs = []
        periods = self.server.get_json("/api/v1/trends/periods")
        for period, path, keys in (
            ("week", "weekly", periods.get("weeks", [])),
            ("month", "monthly", periods.get("months", [])),
        ):
            for key in keys:
                report = self.server.get_json(f"/api/v1/trends/{path}/{key}", missing_ok=True)
                if report and report.get("narrative"):
                    report_jobs.append(
                        Job("report", f"{period}:{key}", "en", "short", {"narrative": report["narrative"]})
                    )
        short = [j for j in short + news_short + report_jobs if self.needed(j)]
        # 긴 본문: 뉴스 본문만 (최근 것부터). 논문 본문은 번역하지 않는다
        full = [j for j in news_full + full if self.needed(j)]
        return short, full

    def _recent_news(self, cutoff: dt.date) -> list[dict]:
        found: list[dict] = []
        offset = 0
        while offset <= 1000:
            page = self.server.get_json("/api/v1/news", {"limit": 50, "offset": offset})
            items = page.get("items", [])
            for item in items:
                if dt.date.fromisoformat(item["published_at"][:10]) < cutoff:
                    return found
                found.append(item)
            if len(items) < 50:
                return found
            offset += 50
        return found

    def _run_short(self, jobs: list[Job]) -> None:
        for lang, size in (("ko", PAPER_TITLE_BATCH), ("en", PAPER_BATCH)):
            group = [j for j in jobs if j.kind == "paper" and j.lang == lang]
            for start in range(0, len(group), size):
                self._batch(lang, group[start : start + size])
        titles = [j for j in jobs if j.kind == "news" and j.lang == "ko"]
        for start in range(0, len(titles), NEWS_TITLE_BATCH):
            self._batch("ko", titles[start : start + NEWS_TITLE_BATCH])
        for job in jobs:
            if job.kind in ("digest", "report") or (job.kind == "news" and job.lang == "en"):
                got = self.translate_object(job.lang, job.source)
                if got is None:
                    self.failed += 1
                else:
                    self._add(job, got)

    def _batch(self, lang: str, group: list[Job]) -> None:
        got = self.translate_batch(lang, {j.key: j.source for j in group})
        for job in group:
            if job.key in got:
                self._add(job, got[job.key])
            else:
                self.failed += 1

    def _run_full(self, jobs: list[Job]) -> None:
        for n, job in enumerate(jobs, start=1):
            text, field = job.source["content"], "content"
            if not text.strip():
                continue
            started = self.clock()
            translated = self.translate_text(job.lang, text)
            if translated is None:
                self.failed += 1
                continue
            self._add(job, {field: translated[:200_000]})
            self.flush()  # 긴 본문은 하나씩 바로 올린다 (중간에 멈춰도 남도록)
            self.log(f"[본문 {n}/{len(jobs)}] {job.kind} {job.key} ({len(text):,}자, {self.clock() - started:.0f}초)")
