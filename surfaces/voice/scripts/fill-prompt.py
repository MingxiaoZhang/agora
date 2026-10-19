#!/usr/bin/env python3
"""Fill a generated voice prompt with session variables, for pasting into the
ElevenLabs dashboard (Phase 0 smoke test). Standard library only.

Usage:
  python3 surfaces/voice/scripts/fill-prompt.py \
      surfaces/voice/generated/agent-prompt.smoke.md \
      surfaces/voice/smoke/transformation.vars.json \
      --out surfaces/voice/smoke/out

Writes <out>/system-prompt.md and <out>/first-message.txt, and prints a size
estimate. Fails if a variable is missing, unused, or still marked EDIT ME.
"""
import argparse
import json
import re
import sys
from pathlib import Path

VAR = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
EDIT_MARK = "EDIT ME"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", type=Path)
    ap.add_argument("vars", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    template = args.prompt.read_text(encoding="utf-8")
    values = json.loads(args.vars.read_text(encoding="utf-8"))

    problems = []
    for k, v in values.items():
        if not isinstance(v, (str, int, float, bool)):
            problems.append(f"{k}: values must be strings, numbers, or booleans")
        elif EDIT_MARK in str(v):
            problems.append(f"{k}: still says {EDIT_MARK!r}; fill it in")

    used = set(VAR.findall(template))
    missing = sorted(used - values.keys() - {"opening_line"})
    if missing:
        problems.append("missing variables: " + ", ".join(missing))
    if "opening_line" not in values:
        problems.append("missing variable: opening_line (becomes the first message)")
    unused = sorted(values.keys() - used - {"opening_line"})
    if unused:
        problems.append("variables not used by this prompt: " + ", ".join(unused))

    if problems:
        print("Cannot fill prompt:", *("  - " + p for p in problems), sep="\n", file=sys.stderr)
        return 1

    filled = VAR.sub(lambda m: str(values[m.group(1)]), template)
    first = str(values["opening_line"])

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "system-prompt.md").write_text(filled, encoding="utf-8")
    (args.out / "first-message.txt").write_text(first + "\n", encoding="utf-8")

    print(f"Wrote {args.out / 'system-prompt.md'} (~{len(filled) // 4} tokens, {len(filled.split())} words)")
    print(f"Wrote {args.out / 'first-message.txt'}")
    if len(filled) // 4 > 4000:
        print("Warning: well over the ~2,000-token guideline; watch turn latency.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
