"""Write the API's OpenAPI schema as JSON without starting a server: `python -m sibyl.openapi [out.json]`."""

import json
import sys
from pathlib import Path

from sibyl.main import app


def main(argv: list[str]) -> None:
    """Write the schema to the path in argv[1], or to stdout."""
    text = json.dumps(app.openapi(), indent=2) + "\n"
    if len(argv) > 1:
        Path(argv[1]).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main(sys.argv)
