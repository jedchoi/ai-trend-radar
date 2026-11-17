# backend 서버 배포

확인된 환경: Linux 서버 + Docker. 구성: `db` (PostgreSQL 16, 볼륨 `radar-pg`) + `api` + `proxy` (Caddy HTTPS). 8000 · 5432 포트는 외부에 열지 않는다.

내 PC (Docker Desktop) 에서 띄울 때는 이 폴더가 아니라 저장소 루트의 `tool/radar-up.sh` 를 쓴다 (`deploy/local/compose.yml`).

## 처음 배포

```sh
# 1) 서버에서 저장소 받기
git clone <이 저장소 주소> ai-trend-radar && cd ai-trend-radar/deploy/server

# 2) 설정
cp .env.example .env
#   RADAR_DOMAIN       서버 IP 를 가리키는 도메인 (DNS A 레코드 필요)
#   POSTGRES_PASSWORD  DB 비밀번호 (openssl rand -hex 24). 처음 한 번 정하면 바꾸지 않는다 (볼륨에 저장됨)
#   INGEST_TOKEN_SHA256 PC 에서 `uv run radar token` 으로 만든 해시
chmod 600 .env

# 3) 방화벽 · 보안 목록에서 80, 443 허용 (클라우드 콘솔과 서버 방화벽 둘 다)

# 4) 실행
docker compose up -d --build
curl -s https://$RADAR_DOMAIN/api/v1/health      # {"status":"ok","latest_date":null}
```

## 이미 80 · 443 을 쓰는 프록시가 있을 때

`proxy` 서비스를 빼고, 기존 프록시에서 `api:8000` (또는 `127.0.0.1:<열어 둔 포트>`) 으로 넘긴다. 그때도 외부에는 HTTPS 만 연다.

## 운영

| 할 일 | 명령 |
| --- | --- |
| 로그 (접근 · 보안 이벤트, JSON 한 줄) | `docker compose logs -f api` |
| 인증 실패만 보기 | `docker compose logs api \| grep auth_failed` |
| 업데이트 | `git pull && docker compose up -d --build` |
| 백업 (하루 1회 cron 권장) | `./backup.sh` (`pg_dump -Fc`, 30일 보관) |
| 복원 | `docker compose exec -T db pg_restore -U radar -d radar --clean --if-exists < backups/radar-YYYYMMDD.dump` |
| DB 접속 | `docker compose exec db psql -U radar -d radar` |
| 되돌리기 | `git checkout <이전 커밋> && docker compose up -d --build` (DB 는 그대로, 필드 추가만 하므로 호환) |
| 토큰 교체 | PC 에서 `radar token` → `.env` 해시 교체 → `docker compose up -d` → PC 키체인 갱신 |
