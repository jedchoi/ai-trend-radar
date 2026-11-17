#!/bin/bash
# 테스트용 PostgreSQL 16 (Docker, 메모리 위 · 비밀번호 없음 · 127.0.0.1:55432). 서버 · 통합 테스트의 기본 주소.
#   tool/test-db.sh         켜기 (이미 켜져 있으면 그대로)
#   tool/test-db.sh --stop  끄기 (데이터는 남지 않음)
# 주소: postgresql://radar@127.0.0.1:55432/radar_test  (다른 DB 를 쓰려면 TEST_DATABASE_URL)
set -euo pipefail
NAME=radar-test-db
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
if [ "${1:-}" = "--stop" ]; then docker rm -f "$NAME" >/dev/null 2>&1 || true; echo "멈춤"; exit 0; fi
if ! docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker run -d --name "$NAME" -p 127.0.0.1:55432:5432 \
    -e POSTGRES_USER=radar -e POSTGRES_HOST_AUTH_METHOD=trust \
    --tmpfs /var/lib/postgresql/data postgres:16-alpine >/dev/null
fi
for _ in $(seq 1 60); do
  docker exec "$NAME" pg_isready -U radar >/dev/null 2>&1 && { echo "테스트 DB 준비: postgresql://radar@127.0.0.1:55432/radar_test"; exit 0; }
  sleep 1
done
echo "테스트 DB 가 뜨지 않습니다: docker logs $NAME"; exit 1
