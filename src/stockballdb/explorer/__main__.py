"""Launch StockBallDB Explorer (Streamlit)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    app_path = Path(__file__).resolve().parent / "app.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.address=localhost",
        "--browser.gatherUsageStats=false",
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
