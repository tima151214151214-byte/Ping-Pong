#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f bot.pid ]]; then
  echo "Bot is not running (no bot.pid)"
  exit 0
fi

PID="$(cat bot.pid)"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "Stop signal sent to pid $PID"
else
  echo "Process $PID is not running"
fi

rm -f bot.pid
