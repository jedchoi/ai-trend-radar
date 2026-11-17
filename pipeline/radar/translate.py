"""번역 (C-P10, 4주기 FR-38 ~ FR-42, BR-P50 · BR-P51): 서버의 요약류를 반대 언어로 미리 만들어 올린다.

- 대상: 논문 한 줄 요약 · 상세 요약 · 용어, 오늘의 세 줄, 뉴스 요약 · 핵심, 리포트 문장 (요약류만)
- 원문 (제목 · 초록 · 본문, 뉴스 제목 · 본문) 은 번역하지 않는다 (FR-41)
- 목표 언어 = 기준 언어의 반대. 기준 언어 = 글에 한글이 있으면 ko, 없으면 en (서버 BR-S50 과 같은 규칙)
- 순서: 최근 날부터. 같은 원본 · 같은 목표 언어는 한 번만 (해시), 바뀌면 다시
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
_HANGUL = re.compile(r"[가-힣]")
# BR-P50: 묶음 크기 (종류별)
BATCH = {"paper": 10, "paper-detail": 3, "news": 5, "digest": 5, "report": 5}
UPLOAD_BATCH = 20
UPLOAD_MAX_CHARS = 3_000_000  # 업로드 한 번 (서버 한도 10 MB, 한글 3바이트)


def base_lang(value: Any) -> str:
    """기준 언어 (서버 BR-S50 과 같은 규칙)."""
    return "ko" if _HANGUL.search(json.dumps(value, ensure_ascii=False)) else "en"


def other_lang(value: Any) -> str:
    return "en" if base_lang(value) == "ko" else "ko"


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
    def group(self) -> str:
        """묶음 단위: 종류 · 목표 언어 (상세 요약이 있는 논문은 따로, 길어서)."""
        kind = "paper-detail" if self.kind == "paper" and "detail" in self.source else self.kind
        return f"{kind}:{self.lang}"

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


class Translator:
    def __init__(
        self,
        provider,
        server,
        state_path,
        max_minutes: int = 180,
        clock: Callable[[], float] = time.monotonic,
        log: Callable[[str], None] = print,
    ) -> None:
        self.provider = provider
        self.server = server
        self.state_path = state_path
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

    def _digest_jobs(self, digest: dict) -> list[Job]:
        day = digest["date"]
        jobs: list[Job] = []
        if digest.get("headline"):
            jobs.append(Job("digest", day, other_lang(digest["headline"]), "short", {"headline": digest["headline"]}))
        for p in digest.get("papers", []):
            source: dict = {"one_liner": p["one_liner"]}
            if p.get("detail"):
                source["detail"] = p["detail"]
            if p.get("glossary"):
                source["glossary"] = p["glossary"]
            jobs.append(Job("paper", p["id"], other_lang(p["one_liner"]), "short", source))
        return jobs

    def _news_job(self, news: dict) -> Job:
        source: dict = {"summary": news["summary"]}
        if news.get("key_points"):
            source["key_points"] = news["key_points"]
        return Job("news", news["id"], other_lang(news["summary"]), "short", source)

    # ---------- 실행 ----------

    def run(self, days: int, today: dt.date) -> dict:
        """BR-P50: 최근 날부터 요약류를 반대 언어로. 결과 요약을 돌려준다."""
        started = self.clock()
        self.deadline = started + self.max_minutes * 60 if self.max_minutes > 0 else None
        stopped = False
        try:
            jobs = self._collect(days, today)
            self.log(f"번역 대상: {len(jobs)}건 (이미 된 것 제외)")
            self._run_jobs(jobs)
            self.flush()
        except StopTranslating:
            self.flush()
            stopped = True
            self.log(f"번역 시간 상한 ({self.max_minutes}분) 에 걸려 멈춤. 다음 실행에서 이어서 합니다")
        return {"done": self.done, "failed": self.failed, "stopped": stopped}

    def _collect(self, days: int, today: dt.date) -> list[Job]:
        cutoff = today - dt.timedelta(days=days)
        jobs: list[Job] = []
        dates = [d["date"] for d in self.server.get_json("/api/v1/digests", {"limit": 90}).get("items", [])]
        for day in dates:  # 최신순
            if dt.date.fromisoformat(day) >= cutoff:
                jobs += self._digest_jobs(self.server.get_json(f"/api/v1/digests/{day}"))
        for brief in self._recent_news(cutoff):
            jobs.append(self._news_job(self.server.get_json(f"/api/v1/news/{brief['id']}")))
        periods = self.server.get_json("/api/v1/trends/periods")
        targets = [("week", "weekly", k) for k in periods.get("weeks", [])]
        targets += [("month", "monthly", k) for k in periods.get("months", [])]
        for period, path, key in targets:
            report = self.server.get_json(f"/api/v1/trends/{path}/{key}", missing_ok=True)
            if report and report.get("narrative"):
                source = {"narrative": report["narrative"]}
                jobs.append(Job("report", f"{period}:{key}", other_lang(report["narrative"]), "short", source))
        return [j for j in jobs if self.needed(j)]

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

    def _run_jobs(self, jobs: list[Job]) -> None:
        groups: dict[str, list[Job]] = {}
        for job in jobs:  # 순서 (최근 것부터) 를 유지한 채 묶음별로
            groups.setdefault(job.group, []).append(job)
        for name, group in groups.items():
            size = BATCH[name.split(":")[0]]
            for start in range(0, len(group), size):
                self._batch(group[0].lang, group[start : start + size])

    def _batch(self, lang: str, group: list[Job]) -> None:
        got = self.translate_batch(lang, {j.key: j.source for j in group})
        for job in group:
            if job.key in got:
                self._add(job, got[job.key])
            else:
                self.failed += 1
