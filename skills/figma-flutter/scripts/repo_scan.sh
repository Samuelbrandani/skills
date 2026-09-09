#!/usr/bin/env bash
# repo_scan.sh — thin wrapper: the Repo Profile is produced by repo_scan.py
# (standard-library Python, runs on macOS, Linux and Windows). Kept so that
# `scripts/repo_scan.sh <root> [feature]` keeps working in docs and habits.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "repo_scan: python3 not found — install Python 3.8+ or run the .py with your interpreter" >&2; exit 1
fi
exec "$PY" "$DIR/repo_scan.py" "$@"
