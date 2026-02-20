#!/usr/bin/env python3
"""Remove `#` comments from Python files under src/sibyl using tokenize.generate_tokens.

This keeps string literals and docstrings intact while removing COMMENT tokens.
"""

import io
import sys
import tokenize
from pathlib import Path


def strip_comments_from_text(text: str) -> str:
    out_tokens = []
    try:
        g = tokenize.generate_tokens(io.StringIO(text).readline)
    except Exception:
        return text

    for tok in g:
        ttype = tok.type
        tstr = tok.string
        if tokenize.tok_name.get(ttype) == "COMMENT":
            continue
        out_tokens.append((ttype, tstr))

    return tokenize.untokenize(out_tokens)


def process_file(path: Path) -> bool:
    text = path.read_text()
    new_text = strip_comments_from_text(text)
    if new_text != text:
        path.write_text(new_text)
        print(f"Modified: {path}")
        return True
    return False


def main():
    base = Path(__file__).resolve().parents[1] / "src" / "sibyl"
    py_files = sorted(base.glob("*.py"))
    modified_any = False
    for p in py_files:
        try:
            if process_file(p):
                modified_any = True
        except Exception as e:
            print(f"Error processing {p}: {e}", file=sys.stderr)
    if not modified_any:
        print("No changes made.")


if __name__ == "__main__":
    main()
