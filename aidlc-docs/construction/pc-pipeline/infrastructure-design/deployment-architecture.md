# Deployment Architecture — pc-pipeline

```text
launchd (06:00, 2주기) → run-daily.sh (로컬 Docker 서버: tool/radar-daily.sh) → (키체인 → 환경 변수) → uv run radar daily
                                                     ├─ HTTPS → huggingface.co
                                                     ├─ HTTPS → AI 제공자 (또는 로컬 CLI · Ollama)
                                                     └─ HTTPS → backend 서버 /api/v1/ingest
```
