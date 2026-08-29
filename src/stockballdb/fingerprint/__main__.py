"""CLI: python -m stockballdb.fingerprint"""

from __future__ import annotations

import json
import sys

from stockballdb.db import get_engine, reset_engine
from stockballdb.fingerprint.compute import compute_database_fingerprint


def main() -> int:
    reset_engine()
    engine = get_engine()
    fp = compute_database_fingerprint(engine)
    print(json.dumps(fp.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
