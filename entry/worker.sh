#!/bin/sh
# Start one background Claude job from a brief file (Linux, macOS, Git Bash).
#
#   worker.sh BRIEF [NAME] [MODEL] [EFFORT]
#   env: SBK_CONFIG_DIR=/path/to/second/account/config   use a different Claude account
#        SBK_CHROME=1                                     the job needs Claude in Chrome
#        SBK_DRYRUN=1                                     print the command only
#
# Two accounts = two quotas you each own, split by task. It is not an automatic fallback for
# when one account hits its limit.
brief="$1"; name="${2:-job}"; model="${3:-sonnet}"; effort="${4:-medium}"
[ -f "$brief" ] || { echo "Brief not found: $brief" >&2; exit 1; }
[ -n "$SBK_CONFIG_DIR" ] && export CLAUDE_CONFIG_DIR="$SBK_CONFIG_DIR"
unset CLAUDE_CODE_OAUTH_TOKEN ANTHROPIC_API_KEY   # they would override the chosen login
logdir="${HOME}/.claude/sbk/logs"; log="$logdir/worker-$name.log"
chrome=""; [ "$SBK_CHROME" = "1" ] && chrome="--chrome"
prompt="Read $brief in full and carry it out to the end. Work autonomously."
if [ "$SBK_DRYRUN" = "1" ]; then
  echo "CLAUDE_CONFIG_DIR=$CLAUDE_CONFIG_DIR"
  echo "claude -p --model $model --effort $effort --permission-mode acceptEdits --name $name --output-format stream-json --verbose $chrome -- \"$prompt\""
  echo "log: $log"
  exit 0
fi
mkdir -p "$logdir"
exec claude -p --model "$model" --effort "$effort" --permission-mode acceptEdits --name "$name" \
  --output-format stream-json --verbose $chrome -- "$prompt" > "$log" 2>&1
