from tests.conftest import make_digest, make_hub, make_paper

# 2026 ISO 주: W42 = 10-12~10-18, W45 = 11-02~11-08, W46 = 11-09~11-15


def _seed_weeks(ingest):
    # W42 ~ W45: agent 키워드 매주 3편, moe 2편 (W44), vision 1편 (W45)
    n = 0

    def pid():
        nonlocal n
        n += 1
        return f"2610.{n:05d}"

    for day in ("2026-10-12", "2026-10-19", "2026-10-26", "2026-11-02"):
        papers = [make_paper(pid(), topic="agents", keywords=["agent"]) for _ in range(3)]
        if day == "2026-10-26":
            papers += [make_paper(pid(), topic="llm-reasoning", keywords=["moe"]) for _ in range(2)]
        if day == "2026-11-02":
            papers += [make_paper(pid(), topic="multimodal-vision", keywords=["vit"])]
        ingest(make_digest(day, papers))
    # W46: agents 3 (agent), llm 3 (moe), rare 2
    w46 = [make_paper(pid(), topic="agents", keywords=["agent"], upvotes=10 + i) for i in range(3)]
    w46 += [make_paper(pid(), topic="llm-reasoning", keywords=["moe"], upvotes=1) for _ in range(3)]
    w46 += [make_paper(pid(), topic="llm-reasoning", keywords=["rare"], upvotes=100 + i) for i in range(2)]
    ingest(make_digest("2026-11-10", w46[:4]))
    ingest(make_digest("2026-11-12", w46[4:]))


def test_topic_counts_with_previous_week(client, ingest):
    # BR-S13 / AC-09-2
    _seed_weeks(ingest)
    report = client.get("/api/v1/trends/weekly/2026-W46").json()
    assert report["start"] == "2026-11-09"
    assert report["end"] == "2026-11-15"
    assert report["paper_count"] == 8
    assert report["topics"] == [
        {"topic": "llm-reasoning", "count": 5, "prev_count": 0, "delta": 5},
        {"topic": "agents", "count": 3, "prev_count": 3, "delta": 0},
        {"topic": "multimodal-vision", "count": 0, "prev_count": 1, "delta": -1},
    ]


def test_rising_keywords_against_four_week_average(client, ingest):
    # BR-S14 / AC-09-3: moe 3 vs 평균 0.5 → 6배, agent 3 vs 3 → 제외, rare 2편 → 제외
    _seed_weeks(ingest)
    report = client.get("/api/v1/trends/weekly/2026-W46").json()
    assert report["baseline_ready"] is True
    assert report["rising_keywords"] == [{"keyword": "moe", "count": 3, "baseline": 0.5, "ratio": 6.0}]


def test_rising_keywords_empty_until_baseline_ready(client, ingest):
    # BR-S15 / AC-09-3: 직전 4주 첫날 이전 데이터 없으면 false + 빈 목록
    ingest(make_digest("2026-11-02", [make_paper("2611.00001", keywords=["x"])]))
    ingest(make_digest("2026-11-10", [make_paper(f"2611.0010{i}", keywords=["moe"]) for i in range(5)]))
    report = client.get("/api/v1/trends/weekly/2026-W46").json()
    assert report["baseline_ready"] is False
    assert report["rising_keywords"] == []


def test_top_papers_by_upvotes(client, ingest):
    # BR-S16 / AC-09-4: 추천 수 상위 5
    _seed_weeks(ingest)
    top = client.get("/api/v1/trends/weekly/2026-W46").json()["top_papers"]
    assert [p["upvotes"] for p in top] == [101, 100, 12, 11, 10]


def test_hub_new_and_steady(client, ingest):
    # BR-S17, BR-S18 / AC-09-5
    ingest(make_digest("2026-11-07", hub=[make_hub("model", 1, "org/old")]))
    ingest(make_digest("2026-11-08", hub=[make_hub("model", 1, "org/old")]))
    ingest(make_digest("2026-11-10", hub=[make_hub("model", 1, "org/old"), make_hub("model", 2, "org/new")]))
    ingest(make_digest("2026-11-11", hub=[make_hub("model", 1, "org/old"), make_hub("model", 2, "org/new")]))
    ingest(make_digest("2026-11-12", hub=[make_hub("model", 1, "org/new"), make_hub("space", 1, "org/sp")]))
    report = client.get("/api/v1/trends/weekly/2026-W46").json()
    assert report["hub_new"] == [
        {"kind": "model", "id": "org/new", "first_seen": "2026-11-10", "days": 3},
        {"kind": "space", "id": "org/sp", "first_seen": "2026-11-12", "days": 1},
    ]
    assert report["hub_steady"] == [
        {"kind": "model", "id": "org/new", "streak_days": 3},
        {"kind": "space", "id": "org/sp", "streak_days": 1},
    ]


def test_latest_week_and_month(client, ingest):
    # BR-S20: 데이터가 있는 가장 최근 기간
    ingest(make_digest("2026-10-30", [make_paper("2610.00001")]))
    ingest(make_digest("2026-11-10", [make_paper("2611.00001")]))
    assert client.get("/api/v1/trends/weekly/latest").json()["key"] == "2026-W46"
    monthly = client.get("/api/v1/trends/monthly/latest").json()
    assert monthly["key"] == "2026-11"
    assert monthly["start"] == "2026-11-01"
    assert monthly["end"] == "2026-11-30"
    assert monthly["topics"][0]["prev_count"] == 1


def test_latest_without_data_is_404(client):
    # BR-S20
    assert client.get("/api/v1/trends/weekly/latest").status_code == 404
    assert client.get("/api/v1/trends/monthly/latest").status_code == 404


def test_period_without_digests_is_404(client, ingest):
    # BR-S20: 지정한 기간에 데이터 없음 → 404
    ingest(make_digest("2026-11-10", [make_paper("2611.00001")]))
    assert client.get("/api/v1/trends/weekly/2026-W40").status_code == 404


def test_invalid_period_keys_are_422(client):
    # 입력 검증
    assert client.get("/api/v1/trends/weekly/2026-W60").status_code == 422
    assert client.get("/api/v1/trends/monthly/2026-13").status_code == 422


def test_series_fills_empty_weeks_with_zero(client, ingest):
    # BR-S19 / AC-10-1
    ingest(make_digest("2026-10-26", [make_paper("2610.00001", topic="agents")]))
    ingest(
        make_digest(
            "2026-11-10", [make_paper("2611.00001", topic="agents"), make_paper("2611.00002", topic="speech-audio")]
        )
    )
    body = client.get("/api/v1/trends/series", params={"weeks": 4}).json()
    assert body["weeks"] == ["2026-W43", "2026-W44", "2026-W45", "2026-W46"]
    assert body["topics"]["agents"] == [0, 1, 0, 1]
    assert body["topics"]["speech-audio"] == [0, 0, 0, 1]
    assert set(body["topics"]) == {
        "llm-reasoning",
        "agents",
        "multimodal-vision",
        "image-video-gen",
        "robotics-physical",
        "speech-audio",
        "training-optimization",
        "evaluation-benchmark",
        "other",
    }


def test_series_weeks_range(client):
    # BR-S19: weeks 1~26
    assert client.get("/api/v1/trends/series", params={"weeks": 27}).status_code == 422
    assert client.get("/api/v1/trends/series").json() == {"weeks": [], "topics": {}}


def test_periods_lists_newest_first(client, ingest):
    # AC-09-1, AC-11-1: 데이터 있는 주 · 월 목록
    ingest(make_digest("2026-10-30", [make_paper("2610.00001")]))
    ingest(make_digest("2026-11-10", [make_paper("2611.00001")]))
    assert client.get("/api/v1/trends/periods").json() == {
        "weeks": ["2026-W46", "2026-W44"],
        "months": ["2026-11", "2026-10"],
    }
