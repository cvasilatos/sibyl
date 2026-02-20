#!/usr/bin/env python3
"""Strip `#` comments from Python files under src/sibyl.

Keeps docstrings and other string literals intact by removing tokens
with type `tokenize.COMMENT` only.
"""

import sys
import tokenize
from io import BytesIO
from pathlib import Path


def strip_file(path: Path) -> bool:
    src = path.read_bytes()
    tokens = []
    try:
        g = tokenize.tokenize(BytesIO(src).readline)
    except Exception:
        return False

    changed = False
    for tok in g:
        ttype = tok.type
        tstr = tok.string
        if tokenize.tok_name.get(ttype) == "COMMENT":
            changed = True
            continue
        tokens.append((ttype, tstr))

    if not changed:
        return False

    new_src = tokenize.untokenize(tokens)
    path.write_bytes(new_src if isinstance(new_src, bytes) else new_src.encode())
    return True


def main():
    base = Path(__file__).resolve().parents[1] / "src" / "sibyl"
    files = sorted(base.glob("*.py"))
    modified = []
    for f in files:
        try:
            if strip_file(f):
                print(f"Stripped comments: {f}")
                modified.append(str(f))
        except Exception as e:
            print(f"Error processing {f}: {e}", file=sys.stderr)

    if not modified:
        print("No files modified.")


if __name__ == "__main__":
    main()
