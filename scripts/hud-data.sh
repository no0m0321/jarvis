#!/usr/bin/env bash
# Jarvis HUD data collector — emits a single-line JSON snapshot.
# Called by the Übersicht widget every refresh tick.
#
# Output schema:
#   {"cpu": <0-100>, "mem": <0-100>, "net_in": <bytes/s>, "net_out": <bytes/s>,
#    "state": "idle|listening|analyzing|speaking", "message": "<text>", "ts": <unix>}

set -e

CACHE_DIR="$HOME/Library/Caches/jarvis-hud"
mkdir -p "$CACHE_DIR"
NET_PREV="$CACHE_DIR/net.prev"

# CPU — use top one-shot; %CPU usage = 100 - idle
CPU=$(top -l 1 -n 0 -s 0 2>/dev/null | awk '/CPU usage/ {gsub(/%/,""); print 100 - $7}' | head -1)
[ -z "$CPU" ] && CPU=0

# Memory — pages active+wired vs total
PAGE_SIZE=$(sysctl -n hw.pagesize 2>/dev/null || echo 16384)
MEM_TOTAL=$(sysctl -n hw.memsize 2>/dev/null || echo 1)
VM=$(vm_stat 2>/dev/null)
PAGES_ACTIVE=$(echo "$VM" | awk '/Pages active/ {gsub(/\./,""); print $3}')
PAGES_WIRED=$(echo "$VM" | awk '/Pages wired down/ {gsub(/\./,""); print $4}')
PAGES_COMP=$(echo "$VM" | awk '/Pages occupied by compressor/ {gsub(/\./,""); print $5}')
[ -z "$PAGES_ACTIVE" ] && PAGES_ACTIVE=0
[ -z "$PAGES_WIRED" ] && PAGES_WIRED=0
[ -z "$PAGES_COMP" ] && PAGES_COMP=0
MEM_USED_BYTES=$(( (PAGES_ACTIVE + PAGES_WIRED + PAGES_COMP) * PAGE_SIZE ))
MEM_PCT=$(awk "BEGIN { printf \"%.1f\", ($MEM_USED_BYTES / $MEM_TOTAL) * 100 }")

# Network — diff against last sample
NET_NOW=$(netstat -ib 2>/dev/null | awk '$1=="en0" && NR>1 {ib+=$7; ob+=$10} END {print ib,ob}')
NOW_TS=$(date +%s)
IN_NOW=$(echo "$NET_NOW" | awk '{print $1+0}')
OUT_NOW=$(echo "$NET_NOW" | awk '{print $2+0}')

NET_IN=0
NET_OUT=0
if [ -f "$NET_PREV" ]; then
  read -r PREV_TS PREV_IN PREV_OUT < "$NET_PREV"
  DT=$(( NOW_TS - PREV_TS ))
  if [ "$DT" -gt 0 ]; then
    NET_IN=$(( (IN_NOW - PREV_IN) / DT ))
    NET_OUT=$(( (OUT_NOW - PREV_OUT) / DT ))
    [ "$NET_IN" -lt 0 ] && NET_IN=0
    [ "$NET_OUT" -lt 0 ] && NET_OUT=0
  fi
fi
echo "$NOW_TS $IN_NOW $OUT_NOW" > "$NET_PREV"

# Jarvis state — read state file written by jarvis.hud module
STATE_FILE="$HOME/Library/Caches/jarvis-hud.json"
if [ -f "$STATE_FILE" ]; then
  STATE=$(cat "$STATE_FILE")
else
  STATE='{"state":"idle","message":"","ts":0}'
fi

# Compose final JSON
printf '{"cpu":%.1f,"mem":%s,"net_in":%d,"net_out":%d,"jarvis":%s,"ts":%d}\n' \
  "$CPU" "$MEM_PCT" "$NET_IN" "$NET_OUT" "$STATE" "$NOW_TS"
