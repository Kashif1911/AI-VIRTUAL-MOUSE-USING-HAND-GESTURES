#!/usr/bin/env python3
"""
AI Virtual Mouse — one launcher for Windows, macOS and Linux.

    python run.py            set everything up (first time), then start the app
    python run.py web        start the web dashboard
    python run.py setup      only install / update dependencies
    python run.py doctor     check this computer and explain any problems

On the first run it automatically:
  * picks a compatible Python (3.9–3.12) and creates a private .venv
  * installs the dependencies (re-installs only if requirements.txt changes)
  * downloads the hand-tracking model if it is missing
"""

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
STAMP = VENV / ".requirements.sha256"

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

MIN_PY, MAX_PY = (3, 9), (3, 12)  # MediaPipe 0.10.20 wheels

HAND_MODEL = ROOT / "hand_landmarker.task"
HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
VOSK_DIR = ROOT / "models" / "vosk-model-small-en-us-0.15"
VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"


def say(msg=""):
    print(msg, flush=True)


# ─────────────────────────────────────────────────────────────
# Python / venv handling
# ─────────────────────────────────────────────────────────────
def py_ok(version):
    return MIN_PY <= tuple(version[:2]) <= MAX_PY


def venv_python():
    return VENV / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def in_our_venv():
    try:
        return Path(sys.prefix).resolve() == VENV.resolve()
    except OSError:
        return False


def probe(cmd):
    """Return (major, minor) for a python command list, or None."""
    try:
        out = subprocess.run(
            cmd + ["-c", "import sys;print(sys.version_info[0],sys.version_info[1])"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0:
            major, minor = out.stdout.split()
            return int(major), int(minor)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return None


def find_compatible_python():
    """Current interpreter if supported, otherwise search the system."""
    if py_ok(sys.version_info):
        return [sys.executable]

    candidates = []
    if IS_WINDOWS:
        candidates += [["py", f"-3.{m}"] for m in (12, 11, 10, 9)]
    candidates += [[f"python3.{m}"] for m in (12, 11, 10, 9)]
    candidates += [["python3"], ["python"]]

    for cmd in candidates:
        if shutil.which(cmd[0]) and (ver := probe(cmd)) and py_ok(ver):
            return cmd
    return None


def explain_python_problem():
    v = f"{sys.version_info[0]}.{sys.version_info[1]}"
    say(f"\n[ERROR] Python {v} is not supported (need 3.9 – 3.12).")
    say("Install Python 3.12 from https://www.python.org/downloads/ and run again.")
    if IS_WINDOWS:
        say("Tip: tick 'Add python.exe to PATH' in the installer.")
    elif IS_MAC:
        say("Tip: brew install python@3.12")
    else:
        say("Tip: sudo apt install python3.12 python3.12-venv   (or your distro's equivalent)")
    sys.exit(1)


def ensure_venv():
    if venv_python().exists():
        return

    py = find_compatible_python()
    if py is None:
        explain_python_problem()

    say(f"[SETUP] Creating virtual environment (.venv) with: {' '.join(py)}")
    result = subprocess.run(py + ["-m", "venv", str(VENV)])
    if result.returncode != 0:
        say("[ERROR] Could not create the virtual environment.")
        if IS_LINUX:
            say("Try: sudo apt install python3-venv")
        sys.exit(1)


def pip(*args, check=True):
    return subprocess.run([str(venv_python()), "-m", "pip", *args], check=check)


def requirements_hash():
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def install_dependencies(force=False):
    ensure_venv()

    if not force and STAMP.exists() and STAMP.read_text().strip() == requirements_hash():
        return

    say("[SETUP] Installing dependencies (first run takes a few minutes)...")
    pip("install", "--upgrade", "pip", "--quiet")

    try:
        pip("install", "-r", str(REQUIREMENTS))
    except subprocess.CalledProcessError:
        say("\n[ERROR] Dependency installation failed. Check your internet "
            "connection and run `python run.py doctor`.")
        sys.exit(1)

    install_pyaudio()
    STAMP.write_text(requirements_hash())
    say("[SETUP] Dependencies installed.")


def install_pyaudio():
    """Microphone support is optional: never fail the setup because of it."""
    probe_cmd = [str(venv_python()), "-c", "import pyaudio"]
    if subprocess.run(probe_cmd, capture_output=True).returncode == 0:
        return

    say("[SETUP] Installing microphone support (PyAudio)...")
    result = pip("install", "PyAudio", check=False)
    if result.returncode == 0:
        return

    say("[WARN] PyAudio could not be installed — voice commands will be disabled.")
    say("       Everything else works. To enable voice later:")
    if IS_LINUX:
        say("       sudo apt install portaudio19-dev python3-dev && python run.py setup --force")
    elif IS_MAC:
        say("       brew install portaudio && python run.py setup --force")
    else:
        say("       python -m pip install PyAudio   (use Python 3.9–3.12)")


# ─────────────────────────────────────────────────────────────
# Model files
# ─────────────────────────────────────────────────────────────
def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    say(f"[SETUP] Downloading {dest.name} ...")
    with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out)
    tmp.replace(dest)


def ensure_models():
    if not HAND_MODEL.exists():
        try:
            download(HAND_MODEL_URL, HAND_MODEL)
        except Exception as err:
            say(f"[ERROR] Could not download the hand model: {err}")
            say(f"        Download it manually from:\n        {HAND_MODEL_URL}")
            say(f"        and place it at: {HAND_MODEL}")
            sys.exit(1)

    if not VOSK_DIR.is_dir():
        try:
            import zipfile
            zip_path = ROOT / "models" / "vosk-model.zip"
            download(VOSK_URL, zip_path)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(ROOT / "models")
            zip_path.unlink(missing_ok=True)
        except Exception as err:
            say(f"[WARN] Voice model not downloaded ({err}). Voice commands disabled.")


# ─────────────────────────────────────────────────────────────
# Doctor
# ─────────────────────────────────────────────────────────────
def doctor():
    say(f"System : {platform.system()} {platform.release()} ({platform.machine()})")
    say(f"Python : {sys.version.split()[0]}  "
        f"{'OK' if py_ok(sys.version_info) else '(unsupported — run.py will find another)'}")
    found = find_compatible_python()
    say(f"Usable Python : {' '.join(found) if found else 'NONE FOUND (install 3.12)'}")
    say(f"Virtual env   : {'present' if venv_python().exists() else 'not created yet'}")
    say(f"Hand model    : {'OK' if HAND_MODEL.exists() else 'missing (auto-downloads on run)'}")
    say(f"Voice model   : {'OK' if VOSK_DIR.is_dir() else 'missing (voice disabled)'}")

    if IS_LINUX:
        session = os.environ.get("XDG_SESSION_TYPE", "unknown")
        say(f"Display       : {session}"
            + ("  <-- Wayland blocks cursor control; log in with 'X11/Xorg'" if session == "wayland" else ""))
        for tool in ("pactl", "amixer", "brightnessctl", "playerctl"):
            say(f"  {tool:<14}: {'found' if shutil.which(tool) else 'not found (optional)'}")
    elif IS_MAC:
        say("macOS permissions needed: Camera, Microphone, Accessibility, Screen Recording")
        say("  (System Settings -> Privacy & Security -> allow your Terminal / IDE)")
        say(f"  brightness CLI: {'found' if shutil.which('brightness') else 'not found (optional: brew install brightness)'}")

    if venv_python().exists():
        say("\nPackage check:")
        for mod in ("cv2", "mediapipe", "pyautogui", "flask", "vosk", "speech_recognition", "pyaudio"):
            ok = subprocess.run([str(venv_python()), "-c", f"import {mod}"],
                                capture_output=True).returncode == 0
            say(f"  {mod:<20}: {'OK' if ok else 'missing'}")


# ─────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────
def start(target):
    install_dependencies()
    ensure_models()

    if target == "web":
        url = f"http://127.0.0.1:{os.environ.get('AI_VM_PORT', '5000')}"
        say(f"[RUN] Web dashboard: {url}   (Ctrl+C to stop)")
        if os.environ.get("AI_VM_NO_BROWSER") != "1":
            try:
                webbrowser.open(url)
            except Exception:
                pass
        script = ROOT / "web" / "app.py"
    else:
        say("[RUN] Starting AI Virtual Mouse (ESC in the camera window to quit)")
        script = ROOT / "main.py"

    try:
        code = subprocess.call([str(venv_python()), str(script)], cwd=str(ROOT))
    except KeyboardInterrupt:
        code = 0
    sys.exit(code)


def main():
    args = [a.lower() for a in sys.argv[1:]]
    command = args[0] if args else "run"

    if command in ("-h", "--help", "help"):
        say(__doc__)
    elif command == "doctor":
        doctor()
    elif command == "setup":
        install_dependencies(force="--force" in args)
        ensure_models()
        say("\n[OK] Setup complete. Start with:  python run.py   (or: python run.py web)")
    elif command in ("run", "desktop", "app"):
        start("desktop")
    elif command in ("web", "dashboard"):
        start("web")
    else:
        say(f"Unknown command '{command}'.\n{__doc__}")
        sys.exit(2)


if __name__ == "__main__":
    main()
