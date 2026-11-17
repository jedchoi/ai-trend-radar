# Deployment Architecture — backend-server

```text
+-----------+    HTTPS 443    +-----------------+  HTTP 8000 (내부)  +-------------------+
| 모바일 앱  | --------------> | proxy (Caddy)   | -----------------> | api (FastAPI)     |
+-----------+                 | TLS, HSTS, 로그 |                    | PostgreSQL (db)   |
+-----------+    HTTPS 443    |                 |                    +-------------------+
| 사용자 PC  | --------------> |                 |
| pipeline  |                 +-----------------+
+-----------+
```

- 업로드는 PC 에서 하루 1~3회, 조회는 앱에서 하루 수십 회 규모
- 백업: `db` 컨테이너에서 `pg_dump -Fc` 하루 1회 (`deploy/server/backup.sh`, 30일 보관). 로컬은 `tool/radar-up.sh --backup`
