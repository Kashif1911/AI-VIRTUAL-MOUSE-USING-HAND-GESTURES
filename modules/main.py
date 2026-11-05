#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         AI VIRTUAL MOUSE — HAND GESTURE CONTROL             ║
║         Entry Point                                          ║
║         License : MIT — License-Free & Copyright-Free        ║
╚══════════════════════════════════════════════════════════════╝

Run with:
    python main.py

Exit:
    Press ESC in the OpenCV window, or Ctrl-C in the terminal.
"""

import sys
import time
import os
import webbrowser

import cv2
import pyautogui
from config                     import CONFIG
from modules.vision_engine      import VisionEngine
from modules.gesture_engine     import GestureEngine, Gesture
from modules.cursor_controller  import CursorController
from modules.ui_renderer        import UIRenderer
from modules.mode_manager       import Mode
from modules.voice_engine       import VoiceEngine


# ══════════════════════════════════════════════════════════════
# STARTUP BANNER
# ══════════════════════════════════════════════════════════════
BANNER = r"""
╔══════════════════════════════════════════════════════╗
║    AI VIRTUAL MOUSE — HAND GESTURE CONTROL           ║
║    Powered by MediaPipe Tasks API  +  OpenCV         ║
╠══════════════════════════════════════════════════════╣
║  GESTURES                                            ║
║  ─────────────────────────────────────────────────  ║
║  Index  + Thumb   →   LEFT CLICK                    ║
║  Middle + Thumb   →   RIGHT CLICK                   ║
║  Ring   + Thumb   →   DRAG & DROP                   ║
║  Index  + Middle  →   SCROLL (tilt hand up/down)    ║
║  Hold Index+Middle + use Thumb → VOLUME MODE         ║
║  Hold Index+Middle+Ring → BRIGHTNESS MODE             ║
║  Hold 4 fingers up    → MEDIA MODE                   ║
║  Open Palm            → EXIT BRIGHTNESS / MEDIA      ║
║  Move Index tip       → CURSOR MOVEMENT              ║
╠══════════════════════════════════════════════════════╣
║  Press ESC to exit.                                  ║
╚══════════════════════════════════════════════════════╝


"""


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    print(BANNER)

    # Disable pyautogui fail-safe (moving to corner won't abort)
    pyautogui.FAILSAFE = False
    screen_w, screen_h = pyautogui.size()

    # ── Initialise all components ────────────────────────
    try:
        vision   = VisionEngine()
        gestures = GestureEngine()
        cursor   = CursorController()
        renderer = UIRenderer()
        voice    = VoiceEngine()
    except FileNotFoundError as err:
        print(err)
        sys.exit(1)
    except RuntimeError as err:
        print(err)
        sys.exit(1)

    print("[INFO] System ready. Show your hand to the camera.\n")
    print("[INFO] Active camera resolution : "
          f"{CONFIG.camera.WIDTH} x {CONFIG.camera.HEIGHT}")
    print(f"[INFO] Screen resolution        : {screen_w} x {screen_h}")
    print(f"[INFO] Max hands tracked        : {CONFIG.model.MAX_HANDS}")
    print()
        # ── Start Voice Assistant ─────────────────────────
    print("[DEBUG] About to start Voice Assistant...", flush=True)
    voice.start()
    print("[DEBUG] Voice Assistant start() completed.", flush=True)

    prev_time       = time.time()
    current_gesture = Gesture.NONE
    voice_exit_requested = False

    def handle_voice_command(command):
        nonlocal voice_exit_requested

        command = command.lower().strip()

        print(f"[VOICE ACTION] {command}")

        if command in ("open chrome", "open google"):
            webbrowser.open("https://www.google.com")

        elif command == "open youtube":
            webbrowser.open("https://www.youtube.com")

        elif command in ("take screenshot", "capture screen"):
            screenshot_path = os.path.join(
                os.path.expanduser("~"),
                "Desktop",
                "AI_Virtual_Mouse_Screenshot.png"
            )

            pyautogui.screenshot(screenshot_path)

            print(
                f"[VOICE] Screenshot saved: {screenshot_path}"
            )

        elif command in ("volume up", "increase volume"):
            pyautogui.press("volumeup")

        elif command in ("volume down", "decrease volume"):
            pyautogui.press("volumedown")

        elif command == "mute":
            pyautogui.press("volumemute")

        elif command == "unmute":
            pyautogui.press("volumemute")

        elif command in ("open file explorer", "open explorer"):
            os.system("explorer")

        elif command in ("close window", "close this window"):
            pyautogui.hotkey("alt", "f4")

        elif command == "stop":
            print("[VOICE] Voice assistant stopped.")
            voice.stop()

        elif command == "exit":
            print("[VOICE] Exit command received.")
            voice_exit_requested = True

    # ══════════════════════════════════════════════════════
    # MAIN LOOP
    # ══════════════════════════════════════════════════════
    try:
        while True:

            if voice_exit_requested:
                print("\n[VOICE] Exit command received — exiting.")
                break

            # ── Capture frame + detect landmarks ─────────
            frame, result = vision.read()

            if frame is None:
                print("[WARN] Dropped frame — camera may be busy.")
                continue

            hand_detected = bool(result.hand_landmarks)

            # ── Process hand ──────────────────────────────
            if hand_detected:
                landmarks = result.hand_landmarks[0]
                fw, fh    = frame.shape[1], frame.shape[0]

                # Convert normalised landmarks → pixel coords
                coords = [
                    (int(lm.x * fw), int(lm.y * fh))
                    for lm in landmarks
                ]

                # Draw skeleton onto frame
                if CONFIG.ui.SHOW_LANDMARKS:
                    renderer.draw_landmarks(frame, landmarks)

                # Map index fingertip → screen position
                raw_x, raw_y       = coords[8]
                target_x, target_y = cursor.map_to_screen(
                    raw_x, raw_y,
                    fw, fh,
                    screen_w, screen_h,
                )
                smooth_x, smooth_y = cursor.smooth(target_x, target_y)

                # Detect gesture and execute mouse action
                current_gesture = gestures.detect(coords)

                # Move cursor unless a click was just fired
                # (prevents the cursor from drifting mid-click)
                if (
                    gestures.mode.is_mode(Mode.NORMAL)
                    and current_gesture not in (
                        Gesture.LEFT_CLICK,
                        Gesture.RIGHT_CLICK,
                    )
                ):
                    pyautogui.moveTo(smooth_x, smooth_y)

            else:
                current_gesture = Gesture.NONE

                # Safety net: release mouse if hand disappears mid-drag
                if gestures.dragging:
                    pyautogui.mouseUp()
                    gestures.dragging = False

            # ── FPS calculation ───────────────────────────
            now       = time.time()
            fps       = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now

            # The dashboard already displays the Browser Vision feed and
            # telemetry. Avoid drawing a second HUD and opening an extra
            # OpenCV window in browser mode; this reduces unnecessary CPU/GPU
            # work while desktop actions are being performed.
            if vision.camera_mode == "window":
                renderer.draw_interface(
                    frame,
                    current_gesture,
                    fps,
                    hand_detected,
                    gestures.mode.get_mode(),
                    gestures.volume_percent,
                    gestures.brightness_percent,
                )

                cv2.imshow("AI Virtual Mouse — Hand Gesture Control", frame)

                # ESC (keycode 27) exits the native camera window.
                if (cv2.waitKey(1) & 0xFF) == 27:
                    print("\n[INFO] ESC pressed — exiting.")
                    break

    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt — exiting.")

    # ── Cleanup ───────────────────────────────────────────
    finally:
        if gestures.dragging:
            pyautogui.mouseUp()

    voice.stop()
    vision.release()
    cv2.destroyAllWindows()

    print("[INFO] System closed safely. Goodbye!\n")


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
