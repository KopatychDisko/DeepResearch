"""Local server entrypoint that builds the frontend and serves the FastAPI app."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn

from backend.main import app
from backend.paths import frontend_directory, frontend_dist_directory


def _run_command(command: list[str], working_directory: Path) -> None:
    completed = subprocess.run(
        command,
        cwd=working_directory,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}"
        )


def _ensure_frontend_dependencies(frontend_directory: Path) -> None:
    node_modules_directory: Path = frontend_directory / "node_modules"
    if node_modules_directory.is_dir():
        return
    _run_command(["npm", "install"], working_directory=frontend_directory)


def _build_frontend(frontend_directory: Path) -> None:
    _ensure_frontend_dependencies(frontend_directory=frontend_directory)
    _run_command(["npm", "run", "build"], working_directory=frontend_directory)
    if not frontend_dist_directory().is_dir():
        raise RuntimeError("Frontend build did not produce frontend/dist")


def _open_browser(url: str) -> None:
    if os.environ.get("WSL_DISTRO_NAME") is not None:
        subprocess.Popen(
            ["cmd.exe", "/c", "start", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    import webbrowser

    webbrowser.open(url)


def _wait_for_healthcheck(host: str, port: int, attempts: int, delay_seconds: float) -> None:
    health_url: str = f"http://{host}:{port}/health"
    for _attempt_index in range(attempts):
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(delay_seconds)
    raise RuntimeError(f"Server did not become ready at {health_url}")


def _schedule_browser_open(host: str, port: int, url: str) -> None:
    def _open_when_ready() -> None:
        _wait_for_healthcheck(host=host, port=port, attempts=60, delay_seconds=0.5)
        _open_browser(url=url)

    browser_thread = threading.Thread(target=_open_when_ready, daemon=True)
    browser_thread.start()


def main() -> None:
    """Build the frontend, open a browser when healthy, and run uvicorn on localhost:8000."""
    host: str = "127.0.0.1"
    port: int = 8000
    url: str = f"http://{host}:{port}"

    frontend_dir: Path = frontend_directory()
    if not frontend_dir.is_dir():
        raise RuntimeError(f"Frontend directory not found: {frontend_dir}")

    _build_frontend(frontend_directory=frontend_dir)

    print(f"Employer Due Diligence is starting at {url}")
    print("Press Ctrl+C to stop.")

    _schedule_browser_open(host=host, port=port, url=url)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
