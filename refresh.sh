#!/bin/bash
# Take a snapshot, rebuild the page data, and push docs/data only.
set -euo pipefail
cd "$(dirname "$0")" || { echo "repo folder is missing" >&2; exit 1; }
mkdir -p logs
exec >>logs/refresh.log 2>&1
echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) refresh start"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
PY=(uv run --no-project --with 'openreview-py>=2.9' python)
DRY="${REFRESH_DRY_RUN:-}"  # tests only: skips sign-in, download, and push

if [ -z "$DRY" ]; then
  [ -f .env ] || { echo "no .env file"; exit 1; }
  set +u; set -a; source .env; set +a; set -u
  [ "$(git rev-parse --abbrev-ref HEAD)" = main ] || { echo "not on main, stopping"; exit 1; }
  [ -z "$(git log origin/main..HEAD --oneline)" ] || { echo "main has commits that are not pushed, stopping"; exit 1; }
  export OPENREVIEW_USERNAME="$EMAIL" OPENREVIEW_PASSWORD="$PASSWORD"
  "${PY[@]}" download.py --new
  "${PY[@]}" build_site.py
  "${PY[@]}" tests/test_pipeline.py
fi

git add docs/data
if ! git diff --cached --quiet -- . ':!docs/data'; then
  git reset -q
  echo "a file outside docs/data is staged, nothing committed"
  exit 1
fi
if git diff --cached --quiet; then
  echo "no data change"
  exit 0
fi
id=$(sed -n 's/.*"latest":"\([^"]*\)".*/\1/p' docs/data/site.json)
git commit -q -m "chore(data): snapshot $id"
[ -n "$DRY" ] || git push -q origin main
# Raw snapshots hold review text. Keep the newest two.
"${PY[@]}" tools/prune_snapshots.py snapshots 2
echo "== done: snapshot $id"
