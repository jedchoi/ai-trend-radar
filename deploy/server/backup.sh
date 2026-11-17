#!/bin/bash
# SQLite 백업 (하루 1회 cron 예: 30 3 * * * /home/ubuntu/ai-trend-radar/deploy/server/backup.sh)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p backups
STAMP=$(date +%Y%m%d)
docker compose exec -T api python -c "import sqlite3; s=sqlite3.connect('/data/radar.db'); d=sqlite3.connect('/data/backup.db'); s.backup(d); d.close()"
docker compose cp api:/data/backup.db "backups/radar-$STAMP.db"
find backups -name 'radar-*.db' -mtime +30 -print -exec rm {} \;
echo "backup: backups/radar-$STAMP.db"
