"""NFR-S01: 논문 10,000건 · Hub 3,600행에서 주요 조회 API p95 300 ms 이하. 실행: pytest -m perf"""

import datetime as dt
import random
import statistics
import time

import pytest

from app.repository import Repository
from app.schemas import DigestIngest, Topic

DAYS = 180
PAPERS_PER_DAY = 56
WORDS = [
    "agent",
    "moe",
    "diffusion",
    "reasoning",
    "rl",
    "vision",
    "robot",
    "speech",
    "benchmark",
    "kv-cache",
    "distillation",
    "rag",
    "long-context",
    "video",
    "world-model",
    "quantization",
]


def _seed(database_url: str) -> None:
    rnd = random.Random(7)
    repo = Repository(database_url)
    repo.init()
    start = dt.date(2026, 5, 1)
    pid = 0
    for d in range(DAYS):
        day = start + dt.timedelta(days=d)
        papers = []
        for _ in range(PAPERS_PER_DAY):
            pid += 1
            papers.append(
                {
                    "id": f"26{pid:08d}",
                    "title": f"Paper about {rnd.choice(WORDS)} and {rnd.choice(WORDS)} number {pid}",
                    "abstract": " ".join(rnd.choice(WORDS) for _ in range(120)),
                    "upvotes": rnd.randint(0, 200),
                    "topic": rnd.choice(list(Topic)).value,
                    "keywords": rnd.sample(WORDS, 4),
                    "one_liner": "한 줄 요약 " + rnd.choice(WORDS),
                    "featured": rnd.random() < 0.08,
                }
            )
        hub = [
            {"kind": k, "rank": r, "id": f"org{rnd.randint(0, 40)}/{k}{r}"}
            for k in ("model", "dataset", "space")
            for r in range(1, 8)
        ][:20]
        repo.upsert_digest(DigestIngest.model_validate({"date": day.isoformat(), "papers": papers, "hub": hub}), "t")
    repo.close()


@pytest.mark.perf
def test_p95_under_300ms(client, settings):
    _seed(settings.database_url)
    paths = [
        "/api/v1/digests/latest",
        "/api/v1/papers?q=agent%20moe",
        "/api/v1/papers?topic=agents&featured=true",
        "/api/v1/trends/weekly/latest",
        "/api/v1/trends/monthly/latest",
        "/api/v1/trends/series?weeks=12",
        "/api/v1/papers/2600005000",
    ]
    results = {}
    for path in paths:
        timings = []
        for _ in range(100):
            t0 = time.perf_counter()
            assert client.get(path).status_code == 200, path
            timings.append((time.perf_counter() - t0) * 1000)
        results[path] = statistics.quantiles(timings, n=20)[18]
    print({k: round(v, 1) for k, v in results.items()})
    assert all(v <= 300 for v in results.values()), results
