# Deployment Architecture — pc-pipeline

```text
launchd (08:00) → run-daily.sh → (키체인 → 환경 변수) → uv run radar daily
                                                     ├─ HTTPS → huggingface.co
                                                     ├─ HTTPS → AI 제공자 (또는 로컬 CLI · Ollama)
                                                     └─ HTTPS → backend 서버 /api/v1/ingest
```
