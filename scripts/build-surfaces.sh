#!/usr/bin/env bash
# Regenerate surface files from the core (method/ and formats/).
# Run from anywhere; commit the results. Do not hand-edit generated files.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

method=(method/session.md method/hooks.md method/discussion.md)
formats=(formats/README.md formats/spine.md formats/learner.md formats/idea-card.md formats/session-note.md)

banner() { printf '<!-- Generated from %s by scripts/build-surfaces.sh. Do not edit. -->\n\n' "$1"; }

copy_into() {
  local dest="$1"
  rm -rf "$dest"
  mkdir -p "$dest"
  for f in "${method[@]}"; do
    { banner "$f"; cat "$f"; } > "$dest/$(basename "$f")"
  done
  for f in "${formats[@]}"; do
    { banner "$f"; cat "$f"; } > "$dest/formats-$(basename "$f")"
  done
}

# Claude skill: SKILL.md is hand-written; references/ is generated.
copy_into surfaces/claude-skill/references

# ChatGPT: instructions.md is hand-written; knowledge/ is generated.
copy_into surfaces/chatgpt/knowledge

# AGENTS.md: one file, hand-written header + core concatenated.
{
  cat surfaces/agents-md/header.md
  for f in "${method[@]}" "${formats[@]}"; do
    printf '\n\n---\n\n<!-- %s -->\n\n' "$f"
    # Demote headings one level so the file has a single top-level title.
    sed -E 's/^(#+) /\1# /' "$f"
  done
} > surfaces/agents-md/AGENTS.md

echo "Surfaces rebuilt from method/ and formats/."
