#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f bot.pid ]]; then
  echo "Bot status: stopped"
  exit 0
fi

PID="$(cat bot.pid)"
if kill -0 "$PID" 2>/dev/null; then
  echo "Bot status: running (pid $PID)"
else
  echo "Bot status: stopped (stale pid $PID)"
fi
