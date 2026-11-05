"""
Cross-platform system volume control.

Backends (chosen automatically):
    Windows : pycaw (Core Audio)
    macOS   : osascript
    Linux   : pactl (PulseAudio / PipeWire) or amixer (ALSA)
    other   : harmless in-memory fallback (never crashes the app)

The public API is identical on every platform:
    set_volume(percent) / get_volume() / mute() / unmute() / toggle_mute()
    change(delta)
"""

import re
import threading

from modules.platform_utils import (
    IS_LINUX,
    IS_MAC,
    IS_WINDOWS,
    has_command,
    run_quiet,
)


# ─────────────────────────────────────────────────────────────
# Backends
# ─────────────────────────────────────────────────────────────
class _WindowsBackend:
    name = "Windows (pycaw)"

    def __init__(self):
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        speakers = AudioUtilities.GetSpeakers()

        # Newer pycaw versions wrap the device and expose EndpointVolume
        endpoint = getattr(speakers, "EndpointVolume", None)

        if endpoint is None:
            interface = speakers.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            endpoint = cast(interface, POINTER(IAudioEndpointVolume))

        self._ep = endpoint
        self._min, self._max, _ = self._ep.GetVolumeRange()

    def set(self, percent):
        level = self._min + (percent / 100.0) * (self._max - self._min)
        self._ep.SetMasterVolumeLevel(level, None)

    def get(self):
        current = self._ep.GetMasterVolumeLevel()
        return int((current - self._min) / (self._max - self._min) * 100)

    def set_mute(self, muted):
        self._ep.SetMute(1 if muted else 0, None)

    def get_mute(self):
        return bool(self._ep.GetMute())


class _MacBackend:
    name = "macOS (osascript)"

    def __init__(self):
        if not has_command("osascript"):
            raise RuntimeError("osascript not found")
        if self.get() is None:
            raise RuntimeError("cannot read volume")

    @staticmethod
    def _osa(script):
        return run_quiet(["osascript", "-e", script])

    def set(self, percent):
        self._osa(f"set volume output volume {int(percent)}")

    def get(self):
        out = self._osa("output volume of (get volume settings)")
        try:
            return int(out.strip())
        except (AttributeError, ValueError):
            return None

    def set_mute(self, muted):
        self._osa(f"set volume output muted {'true' if muted else 'false'}")

    def get_mute(self):
        out = self._osa("output muted of (get volume settings)")
        return bool(out) and out.strip() == "true"


class _PactlBackend:
    name = "Linux (pactl)"

    def __init__(self):
        if not has_command("pactl"):
            raise RuntimeError("pactl not found")
        if self.get() is None:
            raise RuntimeError("no PulseAudio/PipeWire server")

    def set(self, percent):
        run_quiet(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{int(percent)}%"])

    def get(self):
        out = run_quiet(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        match = re.search(r"(\d+)%", out or "")
        return int(match.group(1)) if match else None

    def set_mute(self, muted):
        run_quiet(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if muted else "0"])

    def get_mute(self):
        out = run_quiet(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
        return bool(out) and "yes" in out.lower()


class _AmixerBackend:
    name = "Linux (amixer)"

    def __init__(self):
        if not has_command("amixer"):
            raise RuntimeError("amixer not found")
        if self.get() is None:
            raise RuntimeError("amixer cannot read volume")

    def set(self, percent):
        run_quiet(["amixer", "-q", "sset", "Master", f"{int(percent)}%"])

    def get(self):
        out = run_quiet(["amixer", "sget", "Master"])
        match = re.search(r"\[(\d+)%\]", out or "")
        return int(match.group(1)) if match else None

    def set_mute(self, muted):
        run_quiet(["amixer", "-q", "sset", "Master", "mute" if muted else "unmute"])

    def get_mute(self):
        out = run_quiet(["amixer", "sget", "Master"])
        return bool(out) and "[off]" in out


class _SoftwareBackend:
    """Last-resort fallback: remembers the value but controls nothing."""

    name = "none (volume control unavailable on this system)"

    def __init__(self):
        self._vol = 50
        self._muted = False

    def set(self, percent):
        self._vol = int(percent)

    def get(self):
        return self._vol

    def set_mute(self, muted):
        self._muted = bool(muted)

    def get_mute(self):
        return self._muted


def _pick_backend():
    if IS_WINDOWS:
        candidates = [_WindowsBackend]
    elif IS_MAC:
        candidates = [_MacBackend]
    elif IS_LINUX:
        candidates = [_PactlBackend, _AmixerBackend]
    else:
        candidates = []

    for cls in candidates:
        try:
            return cls()
        except Exception as err:  # missing lib / no audio device
            print(f"[VOLUME] {cls.name} unavailable: {err}")

    backend = _SoftwareBackend()
    print(f"[VOLUME] Using fallback: {backend.name}")
    return backend


# ─────────────────────────────────────────────────────────────
# Public controller
# ─────────────────────────────────────────────────────────────
class VolumeController:
    def __init__(self):
        self._backend = _pick_backend()
        print(f"[VOLUME] Backend: {self._backend.name}")

        # Subprocess-based backends are slow, so the actual change is
        # applied on a worker thread that always uses the latest value.
        self._async = not isinstance(
            self._backend, (_WindowsBackend, _SoftwareBackend)
        )
        self._target = None
        self._last_applied = None
        self._event = threading.Event()
        self._lock = threading.Lock()

        if self._async:
            threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        while True:
            self._event.wait()
            self._event.clear()
            with self._lock:
                value = self._target
            if value is not None and value != self._last_applied:
                self._backend.set(value)
                self._last_applied = value

    def set_volume(self, percent):
        percent = int(max(0, min(100, percent)))

        if self._async:
            with self._lock:
                self._target = percent
            self._event.set()
        else:
            try:
                self._backend.set(percent)
            except Exception as err:
                print(f"[VOLUME] set failed: {err}")

    def get_volume(self):
        try:
            value = self._backend.get()
        except Exception:
            value = None
        return 50 if value is None else max(0, min(100, int(value)))

    def change(self, delta):
        self.set_volume(self.get_volume() + delta)

    def mute(self):
        self._safe_mute(True)

    def unmute(self):
        self._safe_mute(False)

    def toggle_mute(self):
        try:
            self._safe_mute(not self._backend.get_mute())
        except Exception:
            pass

    def _safe_mute(self, muted):
        try:
            self._backend.set_mute(muted)
        except Exception as err:
            print(f"[VOLUME] mute failed: {err}")
