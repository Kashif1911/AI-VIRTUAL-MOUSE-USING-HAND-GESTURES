#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         AI VIRTUAL MOUSE — HAND GESTURE CONTROL             ║
║         UI Renderer — All On-Screen Drawing                  ║
║         License : MIT — License-Free & Copyright-Free        ║
╚══════════════════════════════════════════════════════════════╝
"""

import cv2
from config import CONFIG
from modules.gesture_engine import Gesture
from modules.mode_manager import Mode


# ══════════════════════════════════════════════════════════════
# MEDIAPIPE HAND SKELETON
# ══════════════════════════════════════════════════════════════
_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle
    (5, 9), (9, 10), (10, 11), (11, 12),
    # Ring
    (9, 13), (13, 14), (14, 15), (15, 16),
    # Pinky
    (13, 17), (17, 18), (18, 19), (19, 20),
    # Palm base
    (0, 17),
]

# ══════════════════════════════════════════════════════════════
# GESTURE COLOUR ACCENTS
# ══════════════════════════════════════════════════════════════
_GESTURE_COLOR = {
    Gesture.LEFT_CLICK:  (0,   200, 255),   # Yellow-orange
    Gesture.RIGHT_CLICK: (255, 100,   0),   # Blue
    Gesture.DRAGGING:    (0,   140, 255),   # Orange
    Gesture.SCROLL_UP:   (0,   255, 200),   # Cyan-green
    Gesture.SCROLL_DOWN: (0,   180, 255),   # Orange-yellow
    Gesture.MOVE:        (0,   255, 128),   # Green
    Gesture.NONE:        (150, 150, 150),   # Grey
    Gesture.VOLUME:      (255, 200, 0),     # Cyan-blue
    Gesture.BRIGHTNESS:  (0, 220, 255),     # Brightness
    Gesture.MEDIA:       (255, 120, 200),   # Media
}

# ══════════════════════════════════════════════════════════════
# ON-SCREEN INSTRUCTION TEXT
# ══════════════════════════════════════════════════════════════
_INSTRUCTIONS = [
    "Index  + Thumb   =  LEFT CLICK",
    "Middle + Thumb   =  RIGHT CLICK",
    "Ring   + Thumb   =  DRAG",
    "Index + Middle + Thumb = VOLUME (hold)",
    "Index + Middle + Ring = BRIGHTNESS (hold)",
    "Pinky = MEDIA (hold)",
    "Open Palm = EXIT BRIGHTNESS / MEDIA",
    "Index  + Middle  =  SCROLL",
    "ESC               =  EXIT",
]


class UIRenderer:
    """
    Draws the hand skeleton, HUD header, active-region border,
    and on-screen gesture instructions onto the OpenCV frame.
    """

    # ──────────────────────────────────────────────────────────
    def draw_landmarks(self, frame, hand_landmarks) -> list:
        """
        Draw landmark dots and skeleton connections.

        Parameters
        ----------
        frame         : BGR NumPy array from OpenCV
        hand_landmarks: list of NormalizedLandmark objects

        Returns
        -------
        list of (int, int) pixel coordinates (21 points)
        """
        h, w = frame.shape[:2]
        pts  = []

        for lm in hand_landmarks:
            x = int(lm.x * w)
            y = int(lm.y * h)
            pts.append((x, y))

            # Outer ring (dark) + inner dot (bright)
            cv2.circle(frame, (x, y), 8,  (0, 0, 0),                   -1)
            cv2.circle(frame, (x, y), 6,  CONFIG.ui.LANDMARK_COLOR,     -1)

        for a, b in _CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], CONFIG.ui.CONNECTION_COLOR, 2)

        return pts

    # ──────────────────────────────────────────────────────────
    def draw_interface(
        self,
        frame,
        gesture:       Gesture,
        fps:           float,
        hand_detected: bool,
        mode=Mode.NORMAL,
        volume_percent: int = 0,
        brightness_percent: int = 0,
    ):
        """
        Render the full HUD on top of the camera frame.

        Sections:
          • Header bar with title, FPS, current gesture, status
          • Active-region border rectangle
          • Instruction legend at the bottom
        """
        h, w = frame.shape[:2]
        ui   = CONFIG.ui
        mx   = CONFIG.cursor.MARGIN_X
        my   = CONFIG.cursor.MARGIN_Y

        gesture_color = _GESTURE_COLOR.get(gesture, ui.ACCENT_COLOR)

        # ── Header bar background ─────────────────────────
        cv2.rectangle(frame, (0, 0), (w, 115), ui.HEADER_BG, -1)

        # Thin accent line under the header
        cv2.line(frame, (0, 115), (w, 115), gesture_color, 2)

        # ── Title ─────────────────────────────────────────
        cv2.putText(
            frame, "AI VIRTUAL MOUSE",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0,
            gesture_color, 2, cv2.LINE_AA,
        )

        cv2.putText(
            frame, "HAND GESTURE CONTROL",
            (20, 68),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            ui.TEXT_COLOR, 1, cv2.LINE_AA,
        )

        # ── FPS ───────────────────────────────────────────
        if ui.SHOW_FPS:
            fps_text  = f"FPS: {fps:5.1f}"
            fps_color = (
                ui.STATUS_OK  if fps >= 20 else
                (0, 200, 255) if fps >= 10 else
                ui.STATUS_BAD
            )
            cv2.putText(
                frame, fps_text,
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                fps_color, 1, cv2.LINE_AA,
            )

        # ── Current gesture label ─────────────────────────
        if ui.SHOW_GESTURE:
            cv2.putText(
                frame, f"GESTURE : {gesture.value}",
                (w // 2 - 10, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                gesture_color, 2, cv2.LINE_AA,
            )

        # ── Hand status ───────────────────────────────────
        if hand_detected:
            status_text  = "  HAND DETECTED"
            status_color = ui.STATUS_OK
        else:
            status_text  = "  SEARCHING ..."
            status_color = ui.STATUS_BAD

        cv2.putText(
            frame, status_text,
            (w // 2 - 10, 80),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55,
            status_color, 2, cv2.LINE_AA,
        )

        # ── Active mode / volume HUD ──────────────────────
        mode_name = mode.value if hasattr(mode, "value") else str(mode)
        cv2.putText(
            frame, f"MODE : {mode_name}",
            (w - 230, 100),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            gesture_color, 1, cv2.LINE_AA,
        )

        if mode in (Mode.VOLUME, Mode.BRIGHTNESS):
            # Brightness uses the same vertical level UI as Volume.
            level = volume_percent if mode == Mode.VOLUME else brightness_percent
            label = "VOLUME" if mode == Mode.VOLUME else "BRIGHTNESS"
            bar_x1, bar_y1 = w - 70, 150
            bar_x2, bar_y2 = w - 35, 400
            cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), ui.TEXT_COLOR, 2)
            fill_h = int((bar_y2 - bar_y1) * max(0, min(100, level)) / 100)
            cv2.rectangle(
                frame,
                (bar_x1 + 3, bar_y2 - fill_h),
                (bar_x2 - 3, bar_y2 - 3),
                gesture_color, -1,
            )
            cv2.putText(
                frame, f"{level}%",
                (w - 95, 430),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                gesture_color, 2, cv2.LINE_AA,
            )
            cv2.putText(
                frame, label,
                (w - 105, 455),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                ui.TEXT_COLOR, 1, cv2.LINE_AA,
            )

        # ── Active-region border ───────────────────────────
        cv2.rectangle(
            frame,
            (mx, my + 115),
            (w - mx, h - my),
            ui.REGION_COLOR, 1,
        )
        cv2.putText(
            frame, "CONTROL ZONE",
            (mx + 6, my + 130),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4,
            ui.REGION_COLOR, 1, cv2.LINE_AA,
        )

        # ── Corner markers ────────────────────────────────
        corner_len = 18
        corners = [
            ((mx,         my + 115),           (1,  1)),
            ((w - mx,     my + 115),            (-1, 1)),
            ((mx,         h - my),              (1, -1)),
            ((w - mx,     h - my),              (-1,-1)),
        ]
        for (cx, cy), (dx, dy) in corners:
            cv2.line(frame, (cx, cy), (cx + dx * corner_len, cy),             gesture_color, 2)
            cv2.line(frame, (cx, cy), (cx, cy + dy * corner_len),             gesture_color, 2)

        # ── Instruction legend ────────────────────────────
        if ui.SHOW_INSTRUCTIONS:
            y0 = h - len(_INSTRUCTIONS) * 22 - 10
            for line in _INSTRUCTIONS:
                cv2.putText(
                    frame, line,
                    (20, y0),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.46,
                    ui.TEXT_COLOR, 1, cv2.LINE_AA,
                )
                y0 += 22
