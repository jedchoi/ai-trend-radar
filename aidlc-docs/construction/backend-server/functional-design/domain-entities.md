# Domain Entities — backend-server

| 엔티티 | 저장 (PostgreSQL 테이블, 2주기) | 키 | 주요 속성 | 근거 |
| --- | --- | --- | --- | --- |
| Digest | `digests` | `date` | `headline` (JSON, 0~3줄), `provider`, `updated_at` | FR-11, US-01 |
| Paper | `papers` | `id` | `date`, `title`, `authors`, `abstract`, `published_at`, `upvotes`, `topic`, `keywords`, `one_liner`, `featured`, `detail`, `glossary`, `github_url`, `github_stars`, `project_url`, `organization`, `summary_source` | FR-03, FR-11, US-05 |
| PaperKeyword | `paper_keywords` | (`paper_id`, `keyword`) | 정규화 키워드 (소문자 · 앞뒤 공백 제거) | US-07, US-09 |
| PaperSearch | `papers_fts` (FTS5) | rowid ↔ `papers` | `title`, `one_liner`, `abstract`, `keywords` | FR-12 |
| HubItem | `hub_items` | (`date`, `kind`, `item_id`) | `rank`, `likes`, `downloads`, `trending_score`, `task` | US-03 |
| Report | `reports` | (`period`, `key`) | `narrative`, `provider`, `updated_at` | FR-08, US-11 |
| IngestLog | `ingest_log` | 자동 증가 | `ts`, `kind`, `key`, `client_ip`, `count` (추가만, 삭제 경로 없음) | SECURITY-13 |

값 범위

| 속성 | 규칙 |
| --- | --- |
| `date` | `YYYY-MM-DD`, 2020-01-01 이후 · 오늘 (UTC) + 1일 이하 |
| `Paper.id` | `^[A-Za-z0-9._-]{1,40}$` (arXiv 번호 형식 포함) |
| `topic` | 9개 slug 중 하나 (`services.md`) |
| `summary_source` | `ai` · `hf` · `abstract` |
| `HubItem.kind` | `model` · `dataset` · `space` |
| `HubItem.item_id` | `^[A-Za-z0-9._-]{1,96}/[A-Za-z0-9._-]{1,96}$` |
| 주 키 | `YYYY-Www` (ISO 주), 월 키 `YYYY-MM` |
