#!/usr/bin/env python3
"""
AI VIRTUAL MOUSE — HAND GESTURE CONTROL
Entry Point

Run with:
    python main.py
"""

import sys
import time
import os
import json
import webbrowser

import cv2
import pyautogui

from config import CONFIG
from modules.vision_engine import VisionEngine
from modules.gesture_engine import GestureEngine, Gesture
from modules.cursor_controller import CursorController
from modules.ui_renderer import UIRenderer
from modules.mode_manager import Mode
from modules.platform_utils import (
    close_window_hotkey,
    desktop_dir,
    open_file_manager,
)

try:  # voice is optional: needs vosk + SpeechRecognition + PyAudio
    from modules.voice_engine import VoiceEngine
except Exception as _voice_import_err:  # ImportError on missing packages
    VoiceEngine = None
    _VOICE_IMPORT_ERROR = _voice_import_err
else:
    _VOICE_IMPORT_ERROR = None


BANNER = r"""
╔══════════════════════════════════════════════════════╗
║    AI VIRTUAL MOUSE — HAND GESTURE CONTROL          ║
║    Powered by MediaPipe Tasks API + OpenCV          ║
╠══════════════════════════════════════════════════════╣
║  GESTURES                                            ║
║  ─────────────────────────────────────────────────  ║
║  Index  + Thumb   →   LEFT CLICK                    ║
║  Middle + Thumb   →   RIGHT CLICK                   ║
║  Ring   + Thumb   →   DRAG & DROP                   ║
║  Index  + Middle  →   SCROLL (tilt hand up/down)    ║
║  Hold Index+Middle + use Thumb → VOLUME MODE        ║
║  Hold Index+Middle+Ring → BRIGHTNESS MODE           ║
║  Hold Pinky up     → MEDIA MODE                     ║
║  Open Palm         → EXIT BRIGHTNESS / MEDIA        ║
║  Move Index tip    → CURSOR MOVEMENT                ║
╠══════════════════════════════════════════════════════╣
║  Press ESC to exit (Separate Window mode).          ║
╚══════════════════════════════════════════════════════╝
"""


def main():
    prev_time = time.time()
    last_status_time = 0.0
    last_mouse_x = -1
    last_mouse_y = -1

    camera_mode = os.environ.get("AI_VM_CAMERA_MODE", "window").lower()
    if camera_mode not in ("window", "browser"):
        camera_mode = "window"

    print(BANNER)
    print(f"[INFO] Camera mode: {camera_mode}")

    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0

    status_file = os.path.join(
        os.path.dirname(__file__),
        "web",
        "status.json",
    )

    def write_status(
        running,
        hand_detected=False,
        gesture="NONE",
        fps=0,
        mode="NORMAL",
    ):
        try:
            with open(status_file, "w", encoding="utf-8") as file:
                json.dump(
                    {
                        "running": running,
                        "hand_detected": hand_detected,
                        "gesture": gesture,
                        "fps": round(fps, 1),
                        "mode": mode,
                        "camera_mode": camera_mode,
                    },
                    file,
                )
        except Exception:
            pass

    write_status(True)

    screen_w, screen_h = pyautogui.size()

    # ── Initialise all components ────────────────────────
    try:
        vision = VisionEngine(camera_mode=camera_mode)
        gestures = GestureEngine()
        cursor = CursorController()
        renderer = UIRenderer()
    except FileNotFoundError as err:
        print(err)
        write_status(False)
        sys.exit(1)
    except RuntimeError as err:
        print(err)
        write_status(False)
        sys.exit(1)

    # Voice is optional — the app still works without it
    voice = None
    if VoiceEngine is None:
        print(f"[VOICE] Disabled (missing package: {_VOICE_IMPORT_ERROR})")
    else:
        try:
            voice = VoiceEngine()
        except Exception as err:
            print(f"[VOICE] Disabled: {err}")

    print("[INFO] System ready. Show your hand to the camera.\n")
    print(
        "[INFO] Active camera resolution : "
        f"{CONFIG.camera.WIDTH} x {CONFIG.camera.HEIGHT}"
    )
    print(f"[INFO] Screen resolution        : {screen_w} x {screen_h}")
    print(f"[INFO] Max hands tracked        : {CONFIG.model.MAX_HANDS}")
    print()

    voice_exit_requested = False

    def handle_voice_command(command):
        nonlocal voice_exit_requested

        command = command.lower().strip()

        if not command:
            return

        print(f"[VOICE ACTION] {command}", flush=True)

        if command in ("open chrome", "open google"):
            webbrowser.open("https://www.google.com")

        elif command == "open youtube":
            webbrowser.open("https://www.youtube.com")

        elif command in ("take screenshot", "capture screen"):
            screenshot_path = os.path.join(
                desktop_dir(),
                "AI_Virtual_Mouse_Screenshot.png",
            )
            try:
                pyautogui.screenshot(screenshot_path)
                print(f"[VOICE] Screenshot saved: {screenshot_path}", flush=True)
            except Exception as err:
                print(f"[VOICE] Screenshot failed: {err}", flush=True)

        elif command == "mute":
            gestures.action.mute()

        elif command == "unmute":
            gestures.action.unmute()

        elif command in ("volume up", "increase volume"):
            gestures.action.volume.change(+10)

        elif command in ("volume down", "decrease volume"):
            gestures.action.volume.change(-10)

        elif command in ("open file explorer", "open explorer"):
            open_file_manager()

        elif command in ("close window", "close this window"):
            pyautogui.hotkey(*close_window_hotkey())

        elif command == "stop":
            print("[VOICE] Voice assistant stopped.", flush=True)
            voice.stop()

        elif command == "exit":
            print("[VOICE] Exit command received.", flush=True)
            voice_exit_requested = True

        else:
            print(f"[VOICE] No action mapped for: {command}", flush=True)

    print("[DEBUG] About to start Voice Assistant...", flush=True)

    if voice is not None:
        try:
            voice.start(command_callback=handle_voice_command)
            print("[DEBUG] Voice Assistant start() completed.", flush=True)
        except Exception as err:
            print(f"[VOICE] Failed to start voice assistant: {err}", flush=True)
            voice.stop()
            voice = None

    current_gesture = Gesture.NONE

    try:
        while True:
            if voice_exit_requested:
                print("\n[VOICE] Exit command received — exiting.")
                break

            frame, result = vision.read()

            if frame is None or result is None:
                # Browser Vision waits for the next browser frame.
                if camera_mode == "browser":
                    time.sleep(0.005)
                else:
                    print("[WARN] Dropped frame — camera may be busy.")
                continue

            hand_detected = bool(result.hand_landmarks)

            if hand_detected:
                landmarks = result.hand_landmarks[0]
                fw, fh = frame.shape[1], frame.shape[0]

                coords = [
                    (int(lm.x * fw), int(lm.y * fh))
                    for lm in landmarks
                ]

                if CONFIG.ui.SHOW_LANDMARKS and camera_mode == "window":
                    renderer.draw_landmarks(frame, landmarks)

                raw_x, raw_y = coords[8]
                target_x, target_y = cursor.map_to_screen(
                    raw_x,
                    raw_y,
                    fw,
                    fh,
                    screen_w,
                    screen_h,
                )
                smooth_x, smooth_y = cursor.smooth(target_x, target_y)

                current_gesture = gestures.detect(coords)

                if (
                    gestures.mode.is_mode(Mode.NORMAL)
                    and current_gesture not in (
                        Gesture.LEFT_CLICK,
                        Gesture.RIGHT_CLICK,
                    )
                ):
                    if (
                        abs(smooth_x - last_mouse_x) >= 2
                        or abs(smooth_y - last_mouse_y) >= 2
                    ):
                        pyautogui.moveTo(smooth_x, smooth_y)
                        last_mouse_x = smooth_x
                        last_mouse_y = smooth_y

            else:
                current_gesture = Gesture.NONE

                if gestures.dragging:
                    pyautogui.mouseUp()
                    gestures.dragging = False

            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            if now - last_status_time >= 0.25:
                write_status(
                    True,
                    hand_detected,
                    current_gesture.value,
                    fps,
                    gestures.mode.get_mode().value,
                )
                last_status_time = now

            # The separate-window mode keeps the existing OpenCV UI.
            # Browser Vision intentionally does not create a second
            # camera window; the dashboard owns the video preview.
            if camera_mode == "window":
                renderer.draw_interface(
                    frame,
                    current_gesture,
                    fps,
                    hand_detected,
                    gestures.mode.get_mode(),
                    gestures.volume_percent,
                    gestures.brightness_percent,
                )

                cv2.imshow(
                    "AI Virtual Mouse — Hand Gesture Control",
                    frame,
                )

                if (cv2.waitKey(1) & 0xFF) == 27:
                    print("\n[INFO] ESC pressed — exiting.")
                    break

    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt — exiting.")

    finally:
        write_status(False)

        if gestures.dragging:
            pyautogui.mouseUp()

        if voice is not None:
            voice.stop()

        vision.release()
        cv2.destroyAllWindows()
        print("[INFO] System closed safely. Goodbye!\n")


if __name__ == "__main__":
    main()
