# Domain Entities — pc-pipeline

| 엔티티 | 위치 | 속성 | 비고 |
| --- | --- | --- | --- |
| RawPaper | `models.py` | id, title, authors, abstract, published_at, upvotes, ai_summary, ai_keywords, github_url, github_stars, project_url, organization | Hugging Face 응답을 방어적으로 해석 (없는 필드 허용) |
| HubItem | `models.py` | kind, rank, id, likes, downloads, trending_score, task | 서버 `HubItemIn` 과 같은 필드 |
| AnalyzedPaper | `models.py` | 서버 `PaperIn` 과 같은 필드 | 계약 테스트로 서버 형식과 대조 |
| DigestPayload | `models.py` | date, headline, provider, papers, hub | 서버 `DigestIngest` |
| Config | `config.py` | server (url, token_env, token_file), ai (provider, model, api_key_env, base_url, command, prompt_mode, max_ai_papers, timeout_s), collect, select, paths | TOML |
| RunState | `{data_dir}/state.json` | last_success_date | BR-P13 |
| RunRecord | `{data_dir}/runs.jsonl` | BR-P16 필드 | 추가만 |
| RawArchive | `{data_dir}/raw/{date}.json` | 수집 원본 | 재분석 · 디버깅용 |
