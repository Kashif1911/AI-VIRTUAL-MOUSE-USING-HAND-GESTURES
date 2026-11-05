"""
Action Manager
Central controller for all system actions.
"""

import ctypes

import pyautogui

from modules.platform_utils import IS_LINUX, IS_WINDOWS, has_command, run_quiet
from modules.volume_controller import VolumeController


class ActionManager:

    def __init__(self):
        self.volume = VolumeController()

    # =========================================================
    # MOUSE
    # =========================================================

    def left_click(self):
        pyautogui.click()

    def right_click(self):
        pyautogui.rightClick()

    def mouse_down(self):
        pyautogui.mouseDown()

    def mouse_up(self):
        pyautogui.mouseUp()

    def scroll_up(self, speed):
        pyautogui.scroll(speed)

    def scroll_down(self, speed):
        pyautogui.scroll(-speed)

    # =========================================================
    # VOLUME
    # =========================================================

    def set_volume(self, percent):
        self.volume.set_volume(percent)

    def get_volume(self):
        return self.volume.get_volume()

    def mute(self):
        self.volume.mute()

    def unmute(self):
        self.volume.unmute()

    def toggle_mute(self):
        self.volume.toggle_mute()

    # =========================================================
    # MEDIA CONTROL  (Windows / macOS / Linux)
    # =========================================================

    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_PLAY_PAUSE = 0xB3

    # pyautogui key names + playerctl commands (Linux)
    _KEYS = {
        VK_MEDIA_PLAY_PAUSE: ("playpause", "play-pause"),
        VK_MEDIA_NEXT_TRACK: ("nexttrack", "next"),
        VK_MEDIA_PREV_TRACK: ("prevtrack", "previous"),
    }

    @classmethod
    def _press_media_key(cls, vk_code):
        """Send a media key press using the best method for this OS."""
        key_name, playerctl_cmd = cls._KEYS[vk_code]

        try:
            if IS_WINDOWS:
                user32 = ctypes.windll.user32
                user32.keybd_event(vk_code, 0, 0, 0)  # key down
                user32.keybd_event(vk_code, 0, 2, 0)  # key up
                return

            if IS_LINUX and has_command("playerctl"):
                run_quiet(["playerctl", playerctl_cmd])
                return

            pyautogui.press(key_name)

        except Exception as err:
            print(f"[MEDIA] Could not send '{key_name}': {err}")

    def media_play_pause(self):
        """Play or pause the current media."""
        self._press_media_key(self.VK_MEDIA_PLAY_PAUSE)

    def media_next_track(self):
        """Skip to the next track."""
        self._press_media_key(self.VK_MEDIA_NEXT_TRACK)

    def media_previous_track(self):
        """Go to the previous track."""
        self._press_media_key(self.VK_MEDIA_PREV_TRACK)
