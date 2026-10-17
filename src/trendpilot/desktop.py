"""Open the local TrendPilot UI without leaving a server console running."""

from __future__ import annotations

import subprocess
import sys
import time
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen

URL = "http://127.0.0.1:8788/"
HEALTH_URL = "http://127.0.0.1:8788/health"
SERVER_COMMAND = "from trendpilot.serve import serve; serve()"


def _is_running() -> bool:
    try:
        with urlopen(HEALTH_URL, timeout=0.7) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def launch() -> int:
    """Start the background server if needed, then open the app in a browser."""
    if not _is_running():
        options = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
        }
        if sys.platform == "win32":
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            options["start_new_session"] = True

        try:
            subprocess.Popen([sys.executable, "-c", SERVER_COMMAND], **options)
        except OSError as exc:
            print(f"TrendPilot could not start: {exc}", file=sys.stderr)
            return 1

        for _ in range(40):
            if _is_running():
                break
            time.sleep(0.25)
        else:
            print("TrendPilot server did not start. Try: uv run trendpilot serve", file=sys.stderr)
            return 1

    if not webbrowser.open(URL, new=2):
        print(f"TrendPilot is running at {URL}")
    return 0
