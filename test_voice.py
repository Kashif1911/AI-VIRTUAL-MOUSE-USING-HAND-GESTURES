#!/usr/bin/env python3

import os
import subprocess
import webbrowser
import pyautogui
from datetime import datetime

import pyautogui

from modules.voice_engine import VoiceEngine
from modules.platform_utils import (
    IS_MAC,
    IS_WINDOWS,
    close_window_hotkey,
    open_file_manager,
)


# ============================================================
# VOICE COMMAND ACTIONS
# ============================================================

import subprocess



def open_chrome():
    webbrowser.open("https://www.google.com")
    print("[ACTION] Browser opened.")


def open_google():
    webbrowser.open("https://www.google.com")
    print("[ACTION] Google opened.")


def open_youtube():
    webbrowser.open("https://www.youtube.com")
    print("[ACTION] YouTube opened.")


def close_window():
    #Close the currently active window.
    pyautogui.hotkey(*close_window_hotkey())
    print("[ACTION] Active window closed.")


def close_youtube():
    """Close the current YouTube tab/window."""
    pyautogui.hotkey("command" if IS_MAC else "ctrl", "w")
    print("[ACTION] YouTube closed.")


def close_chrome():
    """Close Chrome completely."""
    if IS_WINDOWS:
        cmd = ["taskkill", "/F", "/IM", "chrome.exe"]
    elif IS_MAC:
        cmd = ["pkill", "-x", "Google Chrome"]
    else:
        cmd = ["pkill", "-f", "chrome"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[ACTION] Chrome closed.")


def take_screenshot():
    """Take a screenshot and save it to Pictures."""

    pictures = os.path.join(
        os.path.expanduser("~"),
        "Pictures"
    )

    os.makedirs(pictures, exist_ok=True)

    filename = (
        "AI_Mouse_Screenshot_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".png"
    )

    filepath = os.path.join(
        pictures,
        filename
    )

    screenshot = pyautogui.screenshot()
    screenshot.save(filepath)

    print(f"[ACTION] Screenshot saved: {filepath}")


def mute_system():
    """Mute/unmute system audio."""

    pyautogui.press("volumemute")
    print("[ACTION] System mute toggled.")


def volume_up():
    """Increase system volume."""

    pyautogui.press("volumeup", presses=3, interval=0.1)
    print("[ACTION] Volume increased.")


def volume_down():
    """Decrease system volume."""

    pyautogui.press("volumedown", presses=3, interval=0.1)
    print("[ACTION] Volume decreased.")


def open_file_explorer():
    """Open the file manager (Explorer / Finder / Files)."""

    open_file_manager()

    print("[ACTION] File Explorer opened.")


def close_window():
    """Close the currently active window."""

    pyautogui.hotkey(*close_window_hotkey())

    print("[ACTION] Active window closed.")


# ============================================================
# COMMAND PROCESSOR
# ============================================================

def handle_command(command):

    command = command.lower().strip()

    print(f"[COMMAND] Processing: {command}")

    # --------------------------------------------------------
    # Chrome
    # --------------------------------------------------------

    if "open chrome" in command:
        open_chrome()

    # --------------------------------------------------------
    # YouTube
    # --------------------------------------------------------

    elif "open youtube" in command or command == "youtube":
        open_youtube()

    # --------------------------------------------------------
    # Google
    # --------------------------------------------------------

    elif "open google" in command or command == "google":
        open_google()

    # --------------------------------------------------------
    # Screenshot
    # --------------------------------------------------------

    elif (
        "take screenshot" in command
        or "screenshot" in command
        or "capture screen" in command
    ):
        take_screenshot()

    # --------------------------------------------------------
    # Mute
    # --------------------------------------------------------

    elif command == "mute":
        mute_system()

    # --------------------------------------------------------
    # Unmute
    # --------------------------------------------------------

    elif command == "unmute":
        unmute_system()

    # --------------------------------------------------------
    # Volume Up
    # --------------------------------------------------------

    elif (
        "volume up" in command
        or "increase volume" in command
        or "increase the volume" in command
    ):
        volume_up()

    # --------------------------------------------------------
    # Volume Down
    # --------------------------------------------------------

    elif (
        "volume down" in command
        or "decrease volume" in command
        or "decrease the volume" in command
    ):
        volume_down()

    # --------------------------------------------------------
    # File Explorer
    # --------------------------------------------------------

    elif (
        "open file explorer" in command
        or "open explorer" in command
        or "file explorer" in command
    ):
        open_file_explorer()

    # --------------------------------------------------------
    # Close YouTube
    # --------------------------------------------------------

    elif (
        "close youtube" in command
        or "close youtube tab" in command
    ):
        close_youtube()

    # --------------------------------------------------------
    # Close Chrome
    # --------------------------------------------------------

    elif (
        "close chrome" in command
        or "exit chrome" in command
    ):
        close_chrome()

    # --------------------------------------------------------
    # Close Window
    # --------------------------------------------------------

    elif (
        "close window" in command
        or "close this window" in command
    ):
        close_window()

    # --------------------------------------------------------
    # Unknown command
    # --------------------------------------------------------

    else:
        print(
            f"[ACTION] No action configured for: {command}"
        )


# ============================================================
# START VOICE ASSISTANT
# ============================================================

voice = VoiceEngine()

voice.start(
    command_callback=handle_command
)


print()
print("=" * 55)
print("        AI VIRTUAL MOUSE — VOICE ASSISTANT")
print("=" * 55)

print()
print("Available commands:")
print()
print("  Open Chrome")
print("  Open Google")
print("  Open YouTube")
print("  Take Screenshot")
print("  Mute")
print("  Volume Up")
print("  Volume Down")
print("  Open File Explorer")
print("  Close Window")
print()
print("Press CTRL+C to stop.")
print("=" * 55)
print()


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:
        pass

except KeyboardInterrupt:

    print(
        "\nStopping voice assistant..."
    )

    voice.stop()