"""예시 데이터로 API 응답을 만들어 contract/samples/ 에 저장한다 (mobile-app 계약 테스트 입력).

실행: python -m tools.make_samples [--out ../contract/samples] [--database-url postgresql://...]
지정한 데이터베이스 (기본: 테스트 서버의 radar_samples) 는 비운 뒤 예시 데이터로 채운다. 운영 DB 를 지정하지 않는다.
예시 논문은 2026-11-13 Daily Papers 의 실제 제목 · id 를 쓰고, 요약 문장은 예시로 작성한 것이다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import random
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repository import Repository

TOKEN = "sample-token"  # noqa: S105 - 예시 DB 전용

FEATURED = [
    {
        "id": "2611.15777",
        "title": "SO-Arena: Benchmarking the Capability Spectrum and Reliability of System One Models",
        "authors": ["Lichen Li", "Ziping Dong", "Sicheng Feng", "Qi Li", "Xinchao Wang"],
        "organization": "National University of Singapore",
        "upvotes": 85,
        "topic": "evaluation-benchmark",
        "keywords": ["system one", "benchmark", "reliability", "reasoning"],
        "one_liner": "긴 추론 없이 바로 답하는 'System One' 모델을 11개 분야에서 평가하는 벤치마크",
        "github_url": "https://github.com/holdrain/SO-Arena",
        "github_stars": 120,
        "detail": {
            "what": "21개 모델을 11개 분야 · 5개 능력군에서 평가하고, 선택지를 바꿨을 때 답이 흔들리는지와 "
            "정답이 없을 때 이를 알아채는지로 신뢰도를 측정했다.",
            "novelty": "정확도와 별개로 '신뢰도' 순위를 따로 매겨, 정확도 1위 모델이 신뢰도에서는 7위에 그친다는 "
            "점을 보였다.",
            "why": "추론 토큰을 쓰지 않는 빠른 모델을 서비스에 넣을 때, 평균 정확도만 보면 위험하다는 근거가 된다.",
            "apply": "사내 분류 · 라우팅에 빠른 모델을 쓸 때 선택지 순서를 섞은 재평가와 '해당 없음' 케이스를 "
            "평가 세트에 넣어 볼 만하다. 코드가 공개돼 있다.",
        },
        "glossary": [
            {"term": "System One 모델", "explanation": "긴 생각 과정 없이 한 번에 답을 내는 빠른 추론 방식의 모델."},
        ],
    },
    {
        "id": "2611.17167",
        "title": "Actor, Judge, or Teacher? Understanding Decision Models in Long-Horizon Agents",
        "authors": ["A. Researcher"],
        "upvotes": 36,
        "topic": "agents",
        "keywords": ["agent", "long-horizon", "llm-as-judge"],
        "one_liner": "긴 작업을 하는 에이전트에서 판단 모델을 행동자 · 심판 · 교사 중 어디에 쓰는 게 나은지 비교",
        "detail": {
            "what": "같은 모델을 행동 결정, 결과 평가, 시범 제공 세 역할로 바꿔 끼우며 장기 과제 성공률을 비교했다.",
            "novelty": "역할별 기여를 분리해 측정한 점.",
            "why": "에이전트 설계에서 큰 모델을 어디에 둘지 비용 대비 효과를 판단하는 데 쓸 수 있다.",
            "apply": "비싼 모델을 모든 단계에 쓰지 말고 평가 단계에만 두는 구성부터 시험해 볼 수 있다.",
        },
        "glossary": [{"term": "LLM-as-judge", "explanation": "언어 모델이 다른 모델의 결과를 채점하게 하는 방식."}],
    },
    {
        "id": "2611.10439",
        "title": "Who Remembers What? Multi-Granularity Memory Extraction for Multi-User, Multi-Agent Interaction",
        "authors": ["B. Researcher"],
        "upvotes": 11,
        "topic": "agents",
        "keywords": ["agent", "memory", "multi-agent"],
        "one_liner": "여러 사용자 · 여러 에이전트 대화에서 누가 무엇을 기억해야 하는지 나눠 저장하는 메모리 추출 방법",
        "detail": {
            "what": "대화에서 개인 · 그룹 · 에이전트 단위 기억을 따로 뽑아 저장하는 방법을 제안했다.",
            "novelty": "기억의 주인과 범위를 명시적으로 나눈다.",
            "why": "팀용 챗봇에서 다른 사람의 정보가 섞여 답하는 문제를 줄인다.",
            "apply": "사내 비서 봇의 메모리를 사용자 · 팀 단위 키로 분리 저장하는 설계에 참고할 수 있다.",
        },
    },
]

OTHERS = [
    (
        "2611.14815",
        "BirdDreams: Joint Perspective and BEV Video Generation for a Plausible, Reactive Driving World Model",
        "robotics-physical",
        ["world model", "driving", "video"],
        56,
        "카메라 영상과 조감도 영상을 함께 생성해 주행 세계 모델의 일관성을 높인 연구",
    ),
    (
        "2611.13004",
        "G-STAR: Group-Scaled Token Capacity for Deeply Compressed Autoregressive Generation",
        "image-video-gen",
        ["autoregressive", "tokenizer", "compression"],
        46,
        "강하게 압축한 토큰으로도 자기회귀 이미지 생성 품질을 지키는 토큰 용량 조절 방법",
    ),
    (
        "2611.15131",
        "Duo: A Reciprocal World Model for Full-Duplex Interaction",
        "speech-audio",
        ["full-duplex", "world model", "speech"],
        45,
        "말하면서 듣는 전이중 대화를 위한 상호 세계 모델",
    ),
    (
        "2611.16748",
        "PhysLoop: Harnessing LLMs' Physics Awareness for Self-Improving Video Generation Models",
        "image-video-gen",
        ["video", "physics", "self-improvement"],
        41,
        "LLM 의 물리 상식으로 영상 생성 모델을 스스로 개선시키는 반복 학습",
    ),
    (
        "2611.15844",
        "Open Vision Banana: A Fully Open Recipe for Generative Visual Perception",
        "multimodal-vision",
        ["vision", "open recipe", "perception"],
        38,
        "생성 모델 기반 시각 인식을 완전 공개 레시피로 재현",
    ),
    (
        "2611.05984",
        "On the Design of Hyper-Connections: Simplification, Stability, and Scalability",
        "training-optimization",
        ["hyper-connections", "residual", "scaling"],
        30,
        "잔차 연결을 일반화한 하이퍼 커넥션을 더 단순하고 안정적으로 만드는 설계",
    ),
    (
        "2611.16961",
        "The Value of Thinking: Learning When to Reason in Hybrid Decision Models",
        "llm-reasoning",
        ["reasoning", "adaptive compute", "agent"],
        9,
        "언제 길게 생각하고 언제 바로 답할지 학습하는 하이브리드 모델",
    ),
    (
        "2611.08219",
        "Agent-R^2: Scaling Agents for Realistic Productivity Work via Real-Source Data Synthesis",
        "agents",
        ["agent", "data synthesis", "productivity"],
        8,
        "실제 업무 자료로 합성한 데이터로 생산성 에이전트를 확장",
    ),
]

HUB = [
    ("model", "Qwen/Qwen3.8-Flash-Next", 4502, 158598, 4286.0, "image-text-to-text"),
    ("model", "zai-org/GLM-5.3-Flash", 1798, 379271, 1694.0, "image-text-to-text"),
    ("model", "MiniMaxAI/MiniMax-H3-Image", 1346, 609130, 1164.0, "text-to-image"),
    ("model", "Lightricks/LTX-2.5", 12290, 2789021, 451.0, "image-to-video"),
    ("dataset", "nvidia/simready-assets", 1187, 1121844, 802.0, None),
    ("dataset", "scenario-labs/3d-collection", 351, 38313, 106.0, None),
    ("space", "pollen-robotics/microduck-simulator", 455, None, 182.0, None),
    ("space", "multimodalart/h3-acceleration-arena", 68, None, 68.0, None),
]

FILLER_TOPICS = [
    "llm-reasoning",
    "agents",
    "multimodal-vision",
    "image-video-gen",
    "training-optimization",
    "evaluation-benchmark",
    "robotics-physical",
    "speech-audio",
]
FILLER_WORDS = ["agent", "reasoning", "moe", "diffusion", "rl", "vision", "benchmark", "rag", "video", "kv-cache"]


def _paper(raw: dict, featured: bool) -> dict:
    return {
        "abstract": f"{raw['title']}. (예시 초록)",
        "authors": raw.get("authors", ["Author"]),
        "featured": featured,
        "summary_source": "ai",
        **raw,
    }


def _history(rnd: random.Random, day: dt.date, n: int, prefix: str) -> list[dict]:
    papers = []
    for i in range(n):
        topic = rnd.choice(FILLER_TOPICS)
        words = rnd.sample(FILLER_WORDS, 2)
        papers.append(
            {
                "id": f"{prefix}.{i:05d}",
                "title": f"Study on {words[0]} and {words[1]} ({day.isoformat()} #{i})",
                "topic": topic,
                "keywords": words,
                "one_liner": f"{words[0]} · {words[1]} 관련 예시 논문",
                "upvotes": rnd.randint(0, 40),
                "featured": i < 3,
                "summary_source": "hf",
            }
        )
    return papers


def build(client: TestClient) -> None:
    rnd = random.Random(42)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    latest = dt.date(2026, 11, 13)
    # 지난 6주: 예시 논문 + Hub (모델 일부는 며칠째 체류)
    for back in range(42, 0, -1):
        day = latest - dt.timedelta(days=back)
        papers = _history(rnd, day, rnd.randint(4, 9), f"26{day.strftime('%m%d')}")
        if back <= 4:  # 최근 에이전트 메모리 논문 증가 → 급상승 키워드
            papers[0]["keywords"] = ["memory", "agent"]
        hub = [
            {"kind": k, "rank": r, "id": i, "likes": lk, "downloads": dl, "trending_score": ts, "task": t}
            for r, (k, i, lk, dl, ts, t) in enumerate(HUB[: 3 + back % 3], start=1)
            if back < 6 or r > 1
        ]
        for r, item in enumerate(hub, start=1):
            item["rank"] = r
        body = {
            "date": day.isoformat(),
            "headline": [f"{day.isoformat()} 예시 요약"],
            "provider": "none",
            "papers": papers,
            "hub": hub,
        }
        client.post("/api/v1/ingest/daily", json=body, headers=headers).raise_for_status()

    papers = [_paper(p, True) for p in FEATURED]
    for paper in papers:
        if paper["id"] == "2611.10439":
            paper["full_text"] = "1 Introduction\n\n(예시 본문) " + paper["abstract"] + "\n\n2 Method\n\n(예시 본문)"
    papers += [
        _paper({"id": i, "title": t, "topic": tp, "keywords": kw, "upvotes": up, "one_liner": ol}, False)
        for i, t, tp, kw, up, ol in OTHERS
    ]
    ranks: dict[str, int] = {}
    hub = []
    for k, i, lk, dl, ts, t in HUB:
        ranks[k] = ranks.get(k, 0) + 1
        hub.append(
            {"kind": k, "rank": ranks[k], "id": i, "likes": lk, "downloads": dl, "trending_score": ts, "task": t}
        )
    body = {
        "date": latest.isoformat(),
        "headline": [
            "빠른 'System One' 모델은 정확도가 높아도 신뢰도는 낮을 수 있다는 평가가 나왔다.",
            "에이전트 연구는 판단 모델의 역할 분담과 다중 사용자 메모리로 옮겨 가고 있다.",
            "영상 · 주행 세계 모델이 물리 일관성을 높이는 방향으로 빠르게 늘고 있다.",
        ],
        "provider": "anthropic",
        "papers": papers,
        "hub": hub,
    }
    client.post("/api/v1/ingest/daily", json=body, headers=headers).raise_for_status()
    client.post(
        "/api/v1/ingest/report",
        json={
            "period": "week",
            "key": "2026-W46",
            "provider": "anthropic",
            "narrative": "이번 주는 에이전트 논문이 가장 많았고, 특히 메모리 관련 키워드가 직전 4주 평균의 몇 배로 "
            "늘었다. 평가 분야에서는 정확도와 신뢰도를 따로 보는 벤치마크가 주목받았다. 다음 주에는 다중 사용자 "
            "메모리 설계가 실제 오픈소스 구현으로 이어지는지 지켜볼 만하다.",
        },
        headers=headers,
    ).raise_for_status()
    client.post(
        "/api/v1/ingest/news", json={"provider": "anthropic", "items": NEWS}, headers=headers
    ).raise_for_status()


# 2026-11-12 ~ 13 Hugging Face 블로그의 실제 제목 · 주소. 본문 · 요약은 예시로 작성한 것
NEWS = [
    {
        "id": "nvidia/simready-assets-robot-pick-and-place",
        "url": "https://huggingface.co/blog/nvidia/simready-assets-robot-pick-and-place",
        "title": "Build a Robot Pick-and-Place Simulation with SimReady Assets",
        "published_at": "2026-11-13T18:00:39Z",
        "organization": "nvidia",
        "content": "(예시 본문) Robot pick-and-place simulation.\n\nSimReady assets come with physics properties.",
        "summary": "물리 속성이 들어 있는 SimReady 자산으로 로봇 집어 옮기기 시뮬레이션을 만드는 방법 (예시 요약)",
        "key_points": ["자산에 질량 · 마찰 같은 물리 속성 포함", "시뮬레이션 데이터로 정책 학습"],
        "keywords": ["robotics", "simulation"],
        "topic": "robotics-physical",
        "summary_source": "ai",
    },
    {
        "id": "allenai/xybench",
        "url": "https://huggingface.co/blog/allenai/xybench",
        "title": "XYBench: Helping with the problem behind the question",
        "published_at": "2026-11-13T17:02:35Z",
        "organization": "allenai",
        "content": "(예시 본문) XYBench measures whether assistants address the underlying problem.",
        "summary": "질문 뒤에 숨은 실제 문제를 돕는지 평가하는 벤치마크 (예시 요약)",
        "key_points": ["XY 문제 상황을 모은 평가 세트", "겉 질문만 답하는 모델을 가려냄"],
        "keywords": ["benchmark", "evaluation"],
        "topic": "evaluation-benchmark",
        "summary_source": "ai",
    },
    {
        "id": "ggml-org/llama-cpp-v1",
        "url": "https://huggingface.co/blog/ggml-org/llama-cpp-v1",
        "title": "llama.cpp v1",
        "published_at": "2026-11-13T14:05:22Z",
        "organization": "ggml-org",
        "content": "(예시 본문) llama.cpp makes it possible to run multi-modal LLMs across a wide range of hardware.",
        "summary": "llama.cpp 가 1.0 을 내고 배포 방식과 지원 하드웨어를 정리했다 (예시 요약)",
        "key_points": ["양자화 · 최적화 백엔드", "C/C++ 이식성"],
        "keywords": ["inference", "quantization"],
        "topic": "training-optimization",
        "summary_source": "ai",
    },
]

SAMPLES = {
    "digest_latest.json": "/api/v1/digests/latest",
    "digests.json": "/api/v1/digests?limit=30",
    "paper_detail.json": "/api/v1/papers/2611.10439",
    "search.json": "/api/v1/papers?q=agent&limit=5",
    "trend_weekly.json": "/api/v1/trends/weekly/latest",
    "trend_monthly.json": "/api/v1/trends/monthly/latest",
    "trend_series.json": "/api/v1/trends/series?weeks=8",
    "trend_periods.json": "/api/v1/trends/periods",
    "news_list.json": "/api/v1/news?limit=20",
    "news_detail.json": "/api/v1/news/ggml-org/llama-cpp-v1",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "contract" / "samples"))
    parser.add_argument(
        "--database-url",
        default=os.environ.get("SAMPLES_DATABASE_URL", "postgresql://radar@127.0.0.1:55432/radar_samples"),
        help="비우고 다시 채울 PostgreSQL 데이터베이스 (없으면 만든다)",
    )
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    repo = Repository(args.database_url)
    repo.init()
    repo.reset()
    repo.close()
    settings = Settings(
        database_url=args.database_url,
        ingest_token_sha256=hashlib.sha256(TOKEN.encode()).hexdigest(),
        public_rate_per_min=10000,
        ingest_rate_per_min=10000,
    )
    with TestClient(create_app(settings)) as client:
        build(client)
        for name, path in SAMPLES.items():
            resp = client.get(path)
            resp.raise_for_status()
            (out / name).write_text(json.dumps(resp.json(), ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"wrote {len(SAMPLES)} samples to {out}")


if __name__ == "__main__":
    main()
