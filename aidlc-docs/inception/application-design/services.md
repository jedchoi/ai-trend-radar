# 서비스와 API 계약 (Services)

backend 서버의 HTTP API 가 세 unit 을 잇는 유일한 계약이다. 형식의 정본은 `server/app/schemas.py` (Pydantic) 이고, 예시 응답은 `contract/samples/` 에 둔다. 경로는 `/api/v1`, 필드는 추가만 한다 (NFR-07).

## 공개 읽기 API (인증 없음, IP 당 분당 120회)

| 메서드 · 경로 | 응답 | Story |
| --- | --- | --- |
| `GET /api/v1/health` | `{status, latest_date}` | 운영 |
| `GET /api/v1/digests?limit=30` | `{items: [DigestSummary]}` | US-01 |
| `GET /api/v1/digests/latest` | `Digest` | US-01 ~ US-03 |
| `GET /api/v1/digests/{date}` | `Digest` | US-01 |
| `GET /api/v1/papers/{id}` | `{paper: Paper, related: [PaperBrief]}` | US-05 ~ US-07 |
| `GET /api/v1/papers?q=&topic=&since=&until=&featured=&limit=&offset=` | `{items: [PaperBrief], total}` | US-12 |
| `GET /api/v1/trends/periods` | `{weeks: [key], months: [key]}` | US-09, US-11 |
| `GET /api/v1/trends/weekly/latest`, `/weekly/{2026-W46}` | `TrendReport` | US-09 |
| `GET /api/v1/trends/monthly/latest`, `/monthly/{2026-11}` | `TrendReport` | US-11 |
| `GET /api/v1/trends/series?weeks=12` | `{weeks: [key], topics: {slug: [count]}}` | US-10 |

## 업로드 API (Bearer 토큰, IP 당 분당 30회)

| 메서드 · 경로 | 요청 | 응답 | Story |
| --- | --- | --- | --- |
| `POST /api/v1/ingest/daily` | `DigestIngest` | `{date, papers}` | US-16, US-19 |
| `POST /api/v1/ingest/report` | `{period, key, narrative, provider}` | `{period, key}` | US-20 |

## 주요 형식

- `DigestIngest`: `date`, `headline` (0~3줄), `provider`, `papers: [PaperIn]` (최대 200), `hub: [HubItemIn]` (최대 60)
- `PaperIn`: `id`, `title`, `authors`, `abstract`, `published_at?`, `upvotes`, `topic`, `keywords`, `one_liner`, `featured`, `detail? {what, novelty, why, apply}`, `glossary [{term, explanation}]`, `github_url?`, `github_stars?`, `project_url?`, `organization?`, `summary_source (ai | hf | abstract)`
- `HubItemIn`: `kind (model | dataset | space)`, `rank`, `id`, `likes`, `downloads?`, `trending_score`, `task?`
- `Digest`: `date`, `headline`, `provider`, `papers: [Paper]`, `hub: [HubItem]` (`is_new`, `streak_days` 추가)
- `Paper` = `PaperIn` + `date`, `hf_url`. `PaperBrief` = `id, title, date, topic, one_liner, upvotes, featured, github_url?`
- `TrendReport`: `period`, `key`, `start`, `end`, `paper_count`, `topics [{topic, count, prev_count, delta}]`, `rising_keywords [{keyword, count, baseline, ratio}]`, `baseline_ready`, `top_papers [PaperBrief]`, `hub_new [{kind, id, first_seen, days}]`, `hub_steady [{kind, id, streak_days}]`, `narrative?`, `narrative_provider?`

## 주제 분류 (고정 9개)

| slug | 한국어 |
| --- | --- |
| `llm-reasoning` | LLM · 추론 |
| `agents` | 에이전트 |
| `multimodal-vision` | 멀티모달 · 비전 |
| `image-video-gen` | 이미지 · 영상 생성 |
| `robotics-physical` | 로보틱스 · 피지컬 AI |
| `speech-audio` | 음성 · 오디오 |
| `training-optimization` | 학습 · 최적화 |
| `evaluation-benchmark` | 평가 · 벤치마크 |
| `other` | 기타 |
