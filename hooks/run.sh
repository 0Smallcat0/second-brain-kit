#!/bin/sh
# Start a hook script with whichever Python 3 exists (python3, python or py), on Linux, macOS
# and Windows (Git Bash). Usage: run.sh <script.py>   (stdin is passed through)
# If no Python 3 is found the hook does nothing and exits 0, so Claude is never blocked.
# Heartbeat: when a Python is found, one tiny file <SBK_HOME>/state/hooks-heartbeat.json records the
# time and the hook that ran. /sbk-status and setup read it: no stamp means the hooks are not running
# (Python or Git Bash missing, or the app was not restarted after an install).
dir=$(dirname "$0")
script="$dir/$1"
home="${SBK_HOME:-$HOME/.sbk}"
[ -d "$home" ] || { [ -z "$SBK_HOME" ] && [ -d "$HOME/.claude/sbk" ] && home="$HOME/.claude/sbk"; }
for py in python3 python py; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)" >/dev/null 2>&1; then
    if [ -d "$home" ]; then
      mkdir -p "$home/state" 2>/dev/null
      printf '{"time": "%s", "hook": "%s"}
' "$(date +%Y-%m-%dT%H:%M:%S)" "$1" > "$home/state/hb.$$" 2>/dev/null         && mv -f "$home/state/hb.$$" "$home/state/hooks-heartbeat.json" 2>/dev/null
    fi
    exec "$py" "$script"
  fi
done
exit 0
