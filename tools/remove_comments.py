#!/usr/bin/env python3
"""Remove all Python comments from target files under src/sibyl.

This script uses the tokenize module to remove COMMENT tokens while preserving
code and string literals.
"""

import tokenize
from pathlib import Path


def strip_comments(path: Path) -> None:
    src = path.read_bytes()
    out_tokens = []
    comment_count = 0
    from io import BytesIO

    try:
        g = tokenize.tokenize(BytesIO(src).readline)
    except Exception:
        g = tokenize.generate_tokens(path.read_text().splitlines(True).__iter__)

    try:
        for tok in g:
            toknum = tok.type
            tokval = tok.string
            if tokenize.tok_name.get(toknum) == "COMMENT":
                comment_count += 1
                continue
            out_tokens.append((toknum, tokval))
    except Exception:
        return

    new_src = tokenize.untokenize(out_tokens)
    path.write_bytes(new_src if isinstance(new_src, bytes) else new_src.encode())
    print(f"Processed {path}: removed {comment_count} comments")


def main():
    base = Path(__file__).resolve().parents[1] / "src" / "sibyl"
    for p in sorted(base.glob("*.py")):
        strip_comments(p)


if __name__ == "__main__":
    main()
