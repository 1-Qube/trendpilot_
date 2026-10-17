"""Read the xAI login Pi already has on this machine. Never print the token."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class AuthError(RuntimeError):
    pass


def bearer_token() -> str:
    env = os.environ.get("XAI_API_KEY", "").strip()
    if env:
        return env

    node = _node()
    launcher = Path.home() / ".pi" / "agent" / "bin" / "pi-launcher.js"
    if not launcher.exists():
        raise AuthError(f"Pi launcher not found at {launcher}")

    proc = subprocess.run(
        [node, str(launcher), "auth", "print-bearer-token", "--provider", "xai"],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    token = (proc.stdout or "").strip()
    if proc.returncode != 0 or not token:
        detail = (proc.stderr or "Pi did not return a token").strip()
        raise AuthError(
            "Could not use the xAI login from Pi. Sign in with /login in Pi, "
            f"or set XAI_API_KEY. {detail[:300]}"
        )
    return token


def _node() -> str:
    env = os.environ.get("PI_NODE", "").strip()
    if env and Path(env).exists():
        return env
    candidate = Path.home() / "AppData" / "Local" / "pi-node" / "current" / "node.exe"
    if candidate.exists():
        return str(candidate)
    found = shutil.which("node")
    if found:
        return found
    raise AuthError("Node is not installed, so Pi cannot refresh the xAI login.")
