# Deployment Architecture — backend-server

```text
+-----------+    HTTPS 443    +-----------------+  HTTP 8000 (내부)  +-------------------+
| 모바일 앱  | --------------> | proxy (Caddy)   | -----------------> | api (FastAPI)     |
+-----------+                 | TLS, HSTS, 로그 |                    | SQLite /data      |
+-----------+    HTTPS 443    |                 |                    +-------------------+
| 사용자 PC  | --------------> |                 |
| pipeline  |                 +-----------------+
+-----------+
```

- 업로드는 PC 에서 하루 1~3회, 조회는 앱에서 하루 수십 회 규모
- 백업: `radar-data` 볼륨의 SQLite 파일을 `sqlite3 .backup` 으로 하루 1회 복사 (Environment Provisioning 의 cron 예시)
