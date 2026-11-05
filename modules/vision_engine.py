#!/usr/bin/env python3
"""
AI VIRTUAL MOUSE — Vision Engine

Supports two camera sources:
    window  -> local OpenCV webcam
    browser -> webcam frames supplied by the dashboard
"""

import os
import cv2
import mediapipe as mp

from config import CONFIG
from modules.browser_frame import BrowserFrameBuffer
from modules.platform_utils import IS_LINUX, IS_MAC, IS_WINDOWS


class VisionEngine:
    def __init__(self, camera_mode=None):
        self.camera_mode = (
            camera_mode
            or os.environ.get("AI_VM_CAMERA_MODE", "window")
        ).lower()

        if self.camera_mode not in ("window", "browser"):
            self.camera_mode = "window"

        if not os.path.exists(CONFIG.model.PATH):
            raise FileNotFoundError(
                f"\n\n[ERROR] Model file not found:\n"
                f"  {CONFIG.model.PATH}\n\n"
                "Please download 'hand_landmarker.task' and place\n"
                "it in the project root directory.\n"
            )

        self._cap = None
        self.camera_index = None
        self._browser_buffer = None
        self._browser_sequence = 0

        if self.camera_mode == "browser":
            self._browser_buffer = BrowserFrameBuffer(create=False)
            print("[CAMERA] Browser Vision source selected.")
        else:
            self._open_local_camera()

        BaseOptions = mp.tasks.BaseOptions
        HandLandmarker = mp.tasks.vision.HandLandmarker
        HandLandmarkerOpts = mp.tasks.vision.HandLandmarkerOptions
        RunningMode = mp.tasks.vision.RunningMode

        options = HandLandmarkerOpts(
            base_options=BaseOptions(
                model_asset_path=CONFIG.model.PATH
            ),
            running_mode=RunningMode.VIDEO,
            num_hands=CONFIG.model.MAX_HANDS,
            min_hand_detection_confidence=CONFIG.model.MIN_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=CONFIG.model.MIN_PRESENCE_CONFIDENCE,
            min_tracking_confidence=CONFIG.model.MIN_TRACKING_CONFIDENCE,
        )

        self._landmarker = HandLandmarker.create_from_options(options)
        self._timestamp = 0

    @staticmethod
    def _camera_backends():
        """Preferred OpenCV capture backends for this OS, default last."""
        if IS_WINDOWS:
            names = ["CAP_DSHOW", "CAP_MSMF"]
        elif IS_MAC:
            names = ["CAP_AVFOUNDATION"]
        elif IS_LINUX:
            names = ["CAP_V4L2"]
        else:
            names = []

        backends = [getattr(cv2, n) for n in names if hasattr(cv2, n)]
        backends.append(cv2.CAP_ANY)
        return backends

    def _open_capture(self, index):
        for backend in self._camera_backends():
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                return cap
            cap.release()
        return None

    def _open_local_camera(self):
        try:
            preferred = int(os.environ.get("AI_VM_CAMERA_INDEX", CONFIG.camera.INDEX))
        except ValueError:
            preferred = CONFIG.camera.INDEX

        camera_indexes = [preferred]

        for index in range(5):
            if index not in camera_indexes:
                camera_indexes.append(index)

        for index in camera_indexes:
            print(f"[CAMERA] Checking camera index {index}...")

            cap = self._open_capture(index)

            if cap is None:
                continue

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG.camera.WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG.camera.HEIGHT)

            ok, test_frame = cap.read()

            if ok and test_frame is not None:
                self._cap = cap
                self.camera_index = index
                print(
                    f"[CAMERA] Camera {index} connected successfully."
                )
                break

            cap.release()

        if self._cap is None:
            raise RuntimeError(
                "\n"
                "╔══════════════════════════════════════════════╗\n"
                "║       NO CAMERA SOURCE DETECTED             ║\n"
                "╠══════════════════════════════════════════════╣\n"
                "║ No usable camera was found on this system.  ║\n"
                "║                                            ║\n"
                "║ Please try:                                ║\n"
                "║ • Enable the built-in camera                ║\n"
                "║ • Connect a USB webcam                      ║\n"
                "║ • Close apps currently using the camera     ║\n"
                "║ • macOS: allow camera access for Terminal   ║\n"
                "║ • Linux: add your user to the 'video' group ║\n"
                "╚══════════════════════════════════════════════╝\n"
            )

    def read(self):
        if self.camera_mode == "browser":
            frame, sequence = self._browser_buffer.read_latest(
                self._browser_sequence,
                timeout=0.10,
            )

            if frame is None:
                return None, None

            self._browser_sequence = sequence
        else:
            ok, frame = self._cap.read()

            if not ok or frame is None:
                print("[WARN] Camera frame read failed.")
                return None, None

        # Mirror so the user sees a natural reflection and cursor
        # movement remains consistent with the existing engine.
        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )

        self._timestamp += 33
        result = self._landmarker.detect_for_video(
            mp_img,
            self._timestamp,
        )

        return frame, result

    def release(self):
        if self._cap is not None:
            self._cap.release()

        if self._browser_buffer is not None:
            self._browser_buffer.close()

        self._landmarker.close()
