"""
Cross-platform screen brightness control.

    Windows / Linux : screen_brightness_control (if installed and supported)
    macOS           : `brightness` CLI  (brew install brightness)
    Linux fallback  : brightnessctl
    otherwise       : harmless in-memory fallback (never crashes the app)
"""

import re

from modules.platform_utils import IS_MAC, has_command, run_quiet

try:  # optional dependency – may not work on every OS / display
    import screen_brightness_control as sbc
except Exception:  # ImportError or platform-specific init error
    sbc = None


class BrightnessController:

    def __init__(self):
        self.min_value = 0
        self.max_value = 100
        self._value = 50
        self._warned = False
        self._backend = self._detect_backend()
        print(f"[BRIGHTNESS] Backend: {self._backend}")

        if self._backend != "none":
            self._value = self._read()

    # ── backend detection ───────────────────────────────────
    def _detect_backend(self):
        if sbc is not None:
            try:
                if sbc.get_brightness():
                    return "sbc"
            except Exception:
                pass

        if IS_MAC and has_command("brightness"):
            return "mac"

        if has_command("brightnessctl"):
            return "brightnessctl"

        return "none"

    # ── raw read / write ────────────────────────────────────
    def _read(self):
        try:
            if self._backend == "sbc":
                return int(sbc.get_brightness()[0])

            if self._backend == "mac":
                out = run_quiet(["brightness", "-l"]) or ""
                match = re.search(r"brightness\s+([0-9.]+)", out)
                if match:
                    return int(float(match.group(1)) * 100)

            if self._backend == "brightnessctl":
                cur = run_quiet(["brightnessctl", "get"])
                mx = run_quiet(["brightnessctl", "max"])
                if cur and mx:
                    return int(int(cur) * 100 / int(mx))
        except Exception:
            pass

        return self._value

    def _write(self, value):
        try:
            if self._backend == "sbc":
                sbc.set_brightness(value)
            elif self._backend == "mac":
                run_quiet(["brightness", f"{value / 100:.2f}"])
            elif self._backend == "brightnessctl":
                run_quiet(["brightnessctl", "set", f"{value}%"])
            elif not self._warned:
                self._warned = True
                print("[BRIGHTNESS] Not supported on this system — ignoring.")
        except Exception:
            pass

    # ── public API (unchanged) ──────────────────────────────
    def get_brightness(self):
        return self._value

    def set_brightness(self, value):
        value = max(self.min_value, min(self.max_value, int(value)))

        if value == self._value:
            return

        self._value = value
        self._write(value)

    def increase(self, step=5):
        self.set_brightness(self.get_brightness() + step)

    def decrease(self, step=5):
        self.set_brightness(self.get_brightness() - step)
