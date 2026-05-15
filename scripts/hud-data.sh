#!/usr/bin/env bash
# Jarvis HUD data collector — emits a single-line JSON snapshot every refresh tick.
#
# Schema:
#   {
#     "cpu": <0-100>, "mem": <0-100>,
#     "net_in": <bytes/s>, "net_out": <bytes/s>,
#     "disk": <0-100 root usage>,
#     "top_proc": "<name>:<%>",
#     "jarvis": {state, message, ts},
#     "voice": {rms, peak, ts},
#     "ts": <unix>
#   }

set -e

CACHE_DIR="$HOME/Library/Caches/jarvis-hud"
mkdir -p "$CACHE_DIR"
NET_PREV="$CACHE_DIR/net.prev"

# ── CPU ───────────────────────────────────────────────────────────────
CPU=$(top -l 1 -n 0 -s 0 2>/dev/null | awk '/CPU usage/ {gsub(/%/,""); print 100 - $7}' | head -1)
[ -z "$CPU" ] && CPU=0

# ── Memory ────────────────────────────────────────────────────────────
PAGE_SIZE=$(sysctl -n hw.pagesize 2>/dev/null || echo 16384)
MEM_TOTAL=$(sysctl -n hw.memsize 2>/dev/null || echo 1)
VM=$(vm_stat 2>/dev/null)
PA=$(echo "$VM" | awk '/Pages active/ {gsub(/\./,""); print $3}'); PA=${PA:-0}
PW=$(echo "$VM" | awk '/Pages wired down/ {gsub(/\./,""); print $4}'); PW=${PW:-0}
PC=$(echo "$VM" | awk '/Pages occupied by compressor/ {gsub(/\./,""); print $5}'); PC=${PC:-0}
MEM_USED=$(( (PA + PW + PC) * PAGE_SIZE ))
MEM_PCT=$(awk "BEGIN { printf \"%.1f\", ($MEM_USED / $MEM_TOTAL) * 100 }")

# ── Network ───────────────────────────────────────────────────────────
NET_NOW=$(netstat -ib 2>/dev/null | awk '$1=="en0" && NR>1 {ib+=$7; ob+=$10} END {print ib,ob}')
NOW_TS=$(date +%s)
IN_NOW=$(echo "$NET_NOW" | awk '{print $1+0}')
OUT_NOW=$(echo "$NET_NOW" | awk '{print $2+0}')

NET_IN=0; NET_OUT=0
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

# ── Disk (root) ───────────────────────────────────────────────────────
DISK=$(df -h / 2>/dev/null | awk 'NR==2 {gsub(/%/,""); print $5}')
[ -z "$DISK" ] && DISK=0

# ── Top process (CPU) ─────────────────────────────────────────────────
TOP_PROC=$(ps -arcwwwxo 'command %cpu' 2>/dev/null | awk 'NR==2 {cpu=$NF; $NF=""; gsub(/^ +| +$/,""); name=$0; printf "%s:%.1f", name, cpu}')
TOP_PROC_ESC=$(printf "%s" "${TOP_PROC:-?:0}" | sed 's/"/\\"/g')

# ── Jarvis state ──────────────────────────────────────────────────────
STATE_FILE="$HOME/Library/Caches/jarvis-hud.json"
if [ -f "$STATE_FILE" ]; then
  STATE=$(cat "$STATE_FILE")
else
  STATE='{"state":"idle","message":"","ts":0}'
fi

# ── Voice level (마이크 RMS) ──────────────────────────────────────────
VOICE_FILE="$HOME/Library/Caches/jarvis-voice.json"
if [ -f "$VOICE_FILE" ]; then
  VOICE=$(cat "$VOICE_FILE")
else
  VOICE='{"rms":0,"peak":0,"ts":0}'
fi

# ── Last log line (daemon stdout) ─────────────────────────────────────
LAST_LOG=$(tail -n 1 "$HOME/Library/Logs/jarvis-wake.out.log" 2>/dev/null | tr -d '"\\' | head -c 80)
LAST_LOG_ESC=$(printf "%s" "${LAST_LOG:-}" | sed 's/[^[:print:]]//g')

# ── Compose ──────────────────────────────────────────────────────────
printf '{"cpu":%.1f,"mem":%s,"net_in":%d,"net_out":%d,"disk":%s,"top_proc":"%s","last_log":"%s","jarvis":%s,"voice":%s,"ts":%d}\n' \
  "$CPU" "$MEM_PCT" "$NET_IN" "$NET_OUT" "$DISK" "$TOP_PROC_ESC" "$LAST_LOG_ESC" "$STATE" "$VOICE" "$NOW_TS"
