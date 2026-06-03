#!/usr/bin/env bash
#
# runs all the tests (backend, frontend, e2e) and prints a pass/fail summary.
# exits non-zero if anything fails so make/ci can use it.
#
# usage:
#   ./check_health.sh             run everything
#   SKIP_E2E=1 ./check_health.sh  skip the slower e2e tests
#
# not using `set -e` on purpose - i want to run every stage and see the whole
# picture, not stop at the first failure. so track failures and exit 1 at the end.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRANK="$ROOT/Frank"
CLIENT="$ROOT/client"
LOG_DIR="$(mktemp -d)"

FAILURES=()

section() { printf '\n=== %s ===\n' "$1"; }

# record <name> <exit_code> <logfile>
record() {
  local name="$1" code="$2" log="$3"
  if [ "$code" -eq 0 ]; then
    printf '  PASS  %s\n' "$name"
  else
    printf '  FAIL  %s (exit %s)\n' "$name" "$code"
    printf '        --- last lines of output ---\n'
    tail -n 15 "$log" | sed 's/^/        /'
    FAILURES+=("$name")
  fi
}

# --- backend: python unit + integration tests --------------------------
section "backend tests (python)"
cd "$FRANK" || exit 2

if [ ! -x ".venv/bin/python" ]; then
  echo "  setting up backend venv (first run)..."
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi

shopt -s nullglob
backend_tests=(test_*.py)
shopt -u nullglob

if [ ${#backend_tests[@]} -eq 0 ]; then
  echo "  (no backend test files found)"
fi

for t in "${backend_tests[@]}"; do
  log="$LOG_DIR/${t}.log"
  ./.venv/bin/python "$t" > "$log" 2>&1
  record "$t" "$?" "$log"
done

# --- frontend: vitest unit/component tests -----------------------------
section "frontend tests (vitest)"
cd "$CLIENT" || exit 2

if [ ! -d node_modules ]; then
  echo "  installing frontend dependencies (first run)..."
  npm install --silent
fi

log="$LOG_DIR/vitest.log"
npm run test:run > "$log" 2>&1
record "vitest unit/component suite" "$?" "$log"

# --- end-to-end: playwright browser tests ------------------------------
section "end-to-end tests (playwright)"
if [ "${SKIP_E2E:-0}" = "1" ]; then
  echo "  SKIPPED (SKIP_E2E=1)"
elif [ ! -d node_modules/@playwright ]; then
  echo "  SKIPPED (playwright not installed - run: npm install && npx playwright install chromium)"
else
  log="$LOG_DIR/playwright.log"
  npm run test:e2e > "$log" 2>&1
  record "playwright e2e suite" "$?" "$log"
fi

# --- summary -----------------------------------------------------------
section "summary"
if [ ${#FAILURES[@]} -eq 0 ]; then
  echo "  ALL CHECKS PASSED - the project is healthy."
  exit 0
fi

echo "  ${#FAILURES[@]} stage(s) FAILED:"
for f in "${FAILURES[@]}"; do
  echo "    - $f"
done
echo "  full logs in: $LOG_DIR"
exit 1
