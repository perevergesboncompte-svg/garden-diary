#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

"${PY:-python3}" build.py

if git diff --quiet && git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
    echo "nothing changed"
    exit 0
fi

git add -A
git commit -q -m "${1:-Update garden diary}"
git push -q origin main
echo "published: https://perevergesboncompte-svg.github.io/garden-diary/"
