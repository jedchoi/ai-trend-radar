# Infrastructure Design — backend-server

## 확인된 환경 (ID-1)

- 사용자는 Linux 서버 (Oracle) 에서 Docker · docker-compose 로 iworship 을 운영 중 (`iworship/deploy_oracle.sh` 에서 확인)
- 서버 주소 · 도메인 · 열린 포트는 확인되지 않음 → 배포 시 사용자가 `.env` 에 넣는 값으로 둔다 (지어내지 않음)

## 구성

| 구성 요소 | 이미지 · 설정 | 노출 |
| --- | --- | --- |
| `api` | `server/Dockerfile` (python:3.12-slim-bookworm, 비 root `app` 사용자, 읽기 전용 루트, `/data` 볼륨) | 내부 네트워크 8000 만 |
| `proxy` | `caddy:2.8.4-alpine`, `deploy/server/Caddyfile` | 80 · 443 (HTTPS 자동 발급, HSTS) |
| 볼륨 | `radar-data` (SQLite), `caddy-data` (인증서) | - |

## 환경 변수 (`deploy/server/.env`, 저장소 밖에서 작성)

| 이름 | 예 | 비고 |
| --- | --- | --- |
| `RADAR_DOMAIN` | `radar.example.com` | 서버 IP 를 가리키는 도메인 (사용자 준비) |
| `INGEST_TOKEN_SHA256` | 64자 hex | `pipeline` 의 `radar token` 명령으로 생성 |
| `ENABLE_DOCS` | `0` | 운영은 0 |

## iworship 과 함께 쓸 때

iworship 이 같은 서버에서 8000 포트를 직접 열고 있다. 이 구성은 8000 을 외부에 열지 않으므로 충돌하지 않는다. 80 · 443 을 다른 프로그램이 쓰고 있으면 Caddy 대신 기존 프록시에 `api:8000` 경로를 추가한다 (`deploy/server/README.md`).
