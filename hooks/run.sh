#!/bin/sh
# Start a hook script with whichever Python 3 exists (python3, python or py), on Linux, macOS
# and Windows (Git Bash). Usage: run.sh <script.py>   (stdin is passed through)
# If no Python 3 is found the hook does nothing and exits 0, so Claude is never blocked.
dir=$(dirname "$0")
script="$dir/$1"
for py in python3 python py; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)" >/dev/null 2>&1; then
    exec "$py" "$script"
  fi
done
exit 0
