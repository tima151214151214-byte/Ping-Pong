#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -f bot.pid ]]; then
  PID="$(cat bot.pid)"
  if kill -0 "$PID" 2>/dev/null; then
    echo "Bot already running (pid $PID)"
    exit 0
  fi
fi

nohup python3 main.py > bot.log 2>&1 &
echo $! > bot.pid
echo "Bot started (pid $(cat bot.pid))"
