#!/usr/bin/env python3
"""Remove full-line and inline `#` comments from Python files under src/sibyl.

This is a blunt tool: it removes any line that begins with `#` (after whitespace)
and removes inline occurrences of ' #' and everything after on the same line.
Use only after confirming this is acceptable.
"""

import sys
from pathlib import Path


def process(path: Path) -> bool:
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    new_lines = []
    changed = False
    for line in lines:
        if line.lstrip().startswith("#"):
            changed = True
            continue
        idx = line.find(" #")
        if idx != -1:
            line = line[:idx].rstrip() + ("\n" if line.endswith("\n") else "")
            changed = True
        new_lines.append(line)

    if changed:
        path.write_text("".join(new_lines))
        print(f"Modified: {path}")
    return changed


def main():
    base = Path(__file__).resolve().parents[1] / "src" / "sibyl"
    files = sorted(base.glob("*.py"))
    any_changed = False
    for f in files:
        try:
            if process(f):
                any_changed = True
        except Exception as e:
            print(f"Error processing {f}: {e}", file=sys.stderr)
    if not any_changed:
        print("No changes made")


if __name__ == "__main__":
    main()
