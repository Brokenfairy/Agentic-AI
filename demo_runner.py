"""One-click demo runner for SkillFlow AI."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from startup_checks import run_startup_checks


def _start_process(args: list[str]) -> subprocess.Popen:
    return subprocess.Popen(args, cwd=str(ROOT))


def main() -> int:
    checks = run_startup_checks()
    print("Startup checks:", checks)

    backend = _start_process(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            settings.API_HOST,
            "--port",
            str(settings.API_PORT),
        ]
    )
    time.sleep(2)
    streamlit = _start_process([sys.executable, "-m", "streamlit", "run", "app.py"])

    print("Backend and Streamlit started. Press Ctrl+C to stop both processes.")
    try:
        backend.wait()
        streamlit.wait()
    except KeyboardInterrupt:
        backend.terminate()
        streamlit.terminate()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
