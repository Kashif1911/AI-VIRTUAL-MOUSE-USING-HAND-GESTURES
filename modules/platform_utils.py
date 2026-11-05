"""
Cross-platform helpers (Windows / macOS / Linux).

Everything OS-specific lives here or in the controller modules, so the rest
of the project never needs to know which operating system it runs on.
"""

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def project_path(*parts):
    """Absolute path inside the project, independent of the working dir."""
    return str(PROJECT_ROOT.joinpath(*parts))


def has_command(name):
    return shutil.which(name) is not None


def run_quiet(cmd, timeout=3):
    """Run a command, return stdout (str) or None on any failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return None


def desktop_dir():
    """Desktop folder if it exists, otherwise the home folder."""
    home = Path.home()

    if IS_LINUX:
        out = run_quiet(["xdg-user-dir", "DESKTOP"])
        if out and Path(out.strip()).is_dir():
            return out.strip()

    desktop = home / "Desktop"
    return str(desktop if desktop.is_dir() else home)


def open_file_manager():
    """Open the OS file manager."""
    try:
        if IS_WINDOWS:
            os.startfile(str(Path.home()))  # noqa: S606
        elif IS_MAC:
            subprocess.Popen(["open", str(Path.home())])
        else:
            subprocess.Popen(["xdg-open", str(Path.home())])
    except OSError as err:
        print(f"[WARN] Could not open file manager: {err}")


def open_url(url):
    webbrowser.open(url)


def close_window_hotkey():
    """Keys that close the focused window on this OS."""
    return ("command", "w") if IS_MAC else ("alt", "f4")
