#!/bin/bash
# PostgreSQL 백업 (하루 1회 cron 예: 30 3 * * * /home/ubuntu/ai-trend-radar/deploy/server/backup.sh)
# 복원: docker compose exec -T db pg_restore -U radar -d radar --clean --if-exists < backups/radar-YYYYMMDD.dump
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p backups
STAMP=$(date +%Y%m%d)
docker compose exec -T db pg_dump -U radar -d radar -Fc > "backups/radar-$STAMP.dump"
find backups -name 'radar-*.dump' -mtime +30 -print -exec rm {} \;
echo "backup: backups/radar-$STAMP.dump"
