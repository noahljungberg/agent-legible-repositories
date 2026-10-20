#!/bin/sh
# Install the completion gate into a git repository. Never overwrites files.
# Usage: templates/completion-gate/install.sh /path/to/repo
set -eu
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
dest=$(CDPATH= cd -- "${1:?usage: install.sh /path/to/repo}" && git rev-parse --show-toplevel)

copy() {
  if [ -e "$dest/$2" ] || [ -L "$dest/$2" ]; then
    echo "skipped $2 (exists; merge $1 by hand)"
  else
    mkdir -p "$(dirname -- "$dest/$2")"
    cp "$src/$1" "$dest/$2"
    echo "added   $2"
  fi
}

copy gate.py .agents/gate/gate.py
copy config.json .agents/gate/config.json
copy skill/SKILL.md .agents/skills/completion-gate/SKILL.md
copy skill/agents/openai.yaml .agents/skills/completion-gate/agents/openai.yaml
copy claude-settings.json .claude/settings.json
copy codex-hooks.json .codex/hooks.json
link=.claude/skills/completion-gate
if [ -e "$dest/$link" ] || [ -L "$dest/$link" ]; then
  echo "skipped $link (exists)"
else
  mkdir -p "$dest/.claude/skills"
  if ln -s ../../.agents/skills/completion-gate "$dest/$link" 2>/dev/null; then
    echo "linked  $link -> .agents/skills/completion-gate"
  else
    echo "could not link $link; copy .agents/skills/completion-gate there instead"
  fi
fi
python3 "$dest/.agents/gate/gate.py" --self-test
echo "Next: set pr_check and protected in .agents/gate/config.json, then commit."
