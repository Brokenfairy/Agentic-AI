"""Single command to run the entire SkillFlow AI stack.

Usage:
    python run_all.py              # Run tests + checks + start backend + UI
    python run_all.py --skip-tests  # Skip pytest and final_check
    python run_all.py --check-only  # Only run tests + checks, do not start servers
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from startup_checks import run_startup_checks


def _run_command(description: str, args: list[str], cwd: Path = ROOT) -> bool:
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}")
    result = subprocess.run(args, cwd=str(cwd))
    return result.returncode == 0


def run_tests() -> bool:
    return _run_command(
        "Running test suite",
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    )


def run_final_check() -> bool:
    return _run_command(
        "Running final readiness check",
        [sys.executable, "final_check.py"],
    )


def start_backend() -> subprocess.Popen:
    print(f"\n{'=' * 60}")
    print("  Starting FastAPI backend")
    print(f"{'=' * 60}")
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            settings.API_HOST,
            "--port",
            str(settings.API_PORT),
        ],
        cwd=str(ROOT),
    )


def start_streamlit() -> subprocess.Popen:
    print(f"\n{'=' * 60}")
    print("  Starting Streamlit UI")
    print(f"{'=' * 60}")
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py"],
        cwd=str(ROOT),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the entire SkillFlow AI stack.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pytest and final_check before starting servers.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only run tests + checks, do not start servers.",
    )
    parser.add_argument(
        "--no-backend",
        action="store_true",
        help="Skip starting the FastAPI backend.",
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="Skip starting the Streamlit UI.",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  SkillFlow AI - Run Everything")
    print("=" * 60)

    # 1. Startup checks
    checks_result = run_startup_checks()
    checks = checks_result.get("checks", [])
    print("\nStartup checks:")
    for check in checks:
        status = "OK" if check["ok"] else "FAIL"
        print(f"  [{status}] {check['name']}: {check['detail']}")

    # 2. Tests + Final Check
    if not args.skip_tests:
        if not run_tests():
            print("\nTests failed. Use --skip-tests to bypass.")
            return 1
        if not run_final_check():
            print("\nFinal check failed. Use --skip-tests to bypass.")
            return 1
    else:
        print("\nSkipped tests and final check (--skip-tests).")

    if args.check_only:
        print("\nCheck-only mode: exiting without starting servers.")
        return 0

    # 3. Start servers
    processes: list[subprocess.Popen] = []

    if not args.no_backend:
        backend_proc = start_backend()
        processes.append(backend_proc)
        time.sleep(2)
        print(f"\nBackend running at http://{settings.API_HOST}:{settings.API_PORT}")

    if not args.no_ui:
        streamlit_proc = start_streamlit()
        processes.append(streamlit_proc)
        print("\nStreamlit UI launching in your browser...")

    if not processes:
        print("\nNo servers started. Exiting.")
        return 0

    print(f"\n{'=' * 60}")
    print("  All services started. Press Ctrl+C to stop.")
    print(f"{'=' * 60}")

    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.wait(timeout=5)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
