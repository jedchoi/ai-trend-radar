#!/bin/bash
# 전체 점검 (CI 와 같은 순서). 사용: tool/check.sh [--skip-app]
#   server · pipeline: ruff, pytest (커버리지 80% 이상), 통합 테스트, 예시 응답 동기화 검사
#   app: flutter analyze · flutter test (flutter 가 있을 때)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKIP_APP=0
[ "${1:-}" = "--skip-app" ] && SKIP_APP=1

step() { printf '\n== %s\n' "$*"; }

step "server"
cd "$ROOT/server"
python3 -m venv .venv >/dev/null 2>&1 || true
.venv/bin/pip install -q -r requirements-dev.txt
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pytest --cov=app --cov-fail-under=80 -q

step "pipeline"
cd "$ROOT/pipeline"
uv sync -q
uv run ruff check . && uv run ruff format --check .
uv run pytest --cov=radar --cov-fail-under=80 -q

step "integration (pipeline → server)"
cd "$ROOT"
PYTHONPATH=server:pipeline server/.venv/bin/python -m pip install -q -e pipeline >/dev/null
PYTHONPATH=server:pipeline server/.venv/bin/pytest integration -q

step "contract samples == app demo assets"
(cd "$ROOT/server" && .venv/bin/python -m tools.make_samples --out /tmp/radar-samples >/dev/null)
diff -r /tmp/radar-samples "$ROOT/contract/samples"
diff -r "$ROOT/contract/samples" "$ROOT/app/assets/demo"

if [ "$SKIP_APP" = 0 ] && command -v flutter >/dev/null 2>&1; then
  step "app"
  cd "$ROOT/app"
  [ -d android ] || tool/bootstrap.sh
  flutter pub get
  flutter analyze --no-fatal-infos
  flutter test
else
  step "app 건너뜀 (flutter 없음 또는 --skip-app)"
fi
echo "모든 점검 통과"
