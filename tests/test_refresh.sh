#!/bin/bash
# Checks that refresh.sh commits only docs/data. No network: REFRESH_DRY_RUN=1.
set -u
repo="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
fail=0
n=0
fresh() {
  n=$((n + 1)); mkdir -p "$tmp/r$n/docs/data" "$tmp/r$n/tools"; cd "$tmp/r$n" || exit 1
  git init -q; git config user.email t@example.com; git config user.name t
  cp "$repo/refresh.sh" .; cp "$repo/tools/prune_snapshots.py" tools/
  echo '{"latest":"2026-01-01T0000Z"}' > docs/data/site.json; echo hi > README.md
  echo logs/ > .gitignore; git add -A; git commit -q -m base
}
count() { git rev-list --count HEAD; }
check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got $2, want $3"; fail=1; fi; }

fresh; echo change >> README.md; git add README.md
REFRESH_DRY_RUN=1 ./refresh.sh; check "outside file: exit code" $? 1; check "outside file: commits" "$(count)" 1

fresh; echo '{"latest":"2026-01-02T0000Z"}' > docs/data/site.json
REFRESH_DRY_RUN=1 ./refresh.sh; check "data change: exit code" $? 0; check "data change: commits" "$(count)" 2
check "data change: message" "$(git log -1 --format=%s)" "chore(data): snapshot 2026-01-02T0000Z"

fresh; REFRESH_DRY_RUN=1 ./refresh.sh; check "no change: exit code" $? 0; check "no change: commits" "$(count)" 1
exit $fail
