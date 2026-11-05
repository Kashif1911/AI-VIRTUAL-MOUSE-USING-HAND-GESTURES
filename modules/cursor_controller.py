#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         AI VIRTUAL MOUSE — HAND GESTURE CONTROL             ║
║         Cursor Controller — Smoothing + Coordinate Mapping   ║
║         License : MIT — License-Free & Copyright-Free        ║
╚══════════════════════════════════════════════════════════════╝
"""

from config import CONFIG
from utils.math_utils import clamp


class CursorController:
    """
    Two responsibilities
    ────────────────────
    1. map_to_screen()  — converts the index-fingertip pixel
       position (inside the camera frame) to a screen coordinate,
       using a configurable margin (dead-zone) on each edge.

    2. smooth()  — applies an exponential moving average so the
       cursor glides rather than jitters when the hand trembles.
    """

    def __init__(self):
        self._sx    = 0.0    # smoothed screen X
        self._sy    = 0.0    # smoothed screen Y
        self._ready = False  # False until first update

    # ──────────────────────────────────────────────────────────
    def map_to_screen(
        self,
        raw_x:    int,
        raw_y:    int,
        frame_w:  int,
        frame_h:  int,
        screen_w: int,
        screen_h: int,
    ) -> tuple:
        """
        Map a fingertip pixel inside the active camera region
        to the full screen coordinate space.

        The margins create a dead-zone border so the user can
        reach every pixel on screen without moving their finger
        to the very edge of the camera frame.

        Parameters
        ----------
        raw_x / raw_y   : fingertip pixel in the camera frame
        frame_w / frame_h : camera resolution
        screen_w / screen_h : monitor resolution

        Returns
        -------
        (screen_x, screen_y) — clamped to screen bounds
        """
        mx = CONFIG.cursor.MARGIN_X
        my = CONFIG.cursor.MARGIN_Y

        # Clamp finger position into the active region
        x = clamp(raw_x, mx, frame_w - mx)
        y = clamp(raw_y, my, frame_h - my)

        # Proportional mapping
        sx = int((x - mx) / (frame_w - 2 * mx) * screen_w)
        sy = int((y - my) / (frame_h - 2 * my) * screen_h)

        return (
            clamp(sx, 0, screen_w - 1),
            clamp(sy, 0, screen_h - 1),
        )

    # ──────────────────────────────────────────────────────────
    def smooth(self, target_x: int, target_y: int) -> tuple:
        """
        Apply exponential moving average (EMA) smoothing.

        α = CONFIG.cursor.SMOOTHING
            0.0 → cursor frozen
            1.0 → raw (no smoothing)
            0.2–0.3 → good balance of stability and responsiveness

        Returns
        -------
        (int, int) — smoothed cursor position
        """
        alpha = CONFIG.cursor.SMOOTHING

        if not self._ready:
            # Initialise on first call so there's no initial jump
            self._sx    = float(target_x)
            self._sy    = float(target_y)
            self._ready = True
        else:
            self._sx += (target_x - self._sx) * alpha
            self._sy += (target_y - self._sy) * alpha

        return int(self._sx), int(self._sy)
