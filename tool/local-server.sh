#!/bin/bash
# (2주기부터) 서버는 Docker Desktop 에서 뜬다: tool/radar-up.sh --server-only 와 같다.
# 전체 (데이터 채우기 · 06:00 일정 · 앱 설치) 는 tool/radar-up.sh
exec "$(dirname "$0")/radar-up.sh" --server-only "$@"
