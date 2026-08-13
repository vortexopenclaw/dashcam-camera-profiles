#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

scan_paths=(README.md CONTRIBUTING.md DESIGN.md LESSONS.md docs examples profiles schemas)
patterns=(
  '/(Users|Volumes|home)/'
  'Ariel([[:space:]]+Bravy)?'
  '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
  '(^|[^[:alnum:]])(192\.168|10|172\.(1[6-9]|2[0-9]|3[01]))(\.[0-9]{1,3}){2,3}([^[:alnum:]]|$)'
  '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
  '(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)["'"'"'[:space:]]*[:=]["'"'"'[:space:]]*[A-Za-z0-9_./+-]{12,}'
)

for pattern in "${patterns[@]}"; do
  if rg --hidden --glob '!docs/data/cameras.json' --glob '!*.svg' -n -i -e "$pattern" "${scan_paths[@]}"; then
    echo "Privacy audit failed: a prohibited pattern was found." >&2
    exit 1
  fi
done

python3 scripts/build-index.py --output "$(mktemp -t dashcam-camera-profiles-index).json" >/dev/null
echo "Privacy audit passed"
