#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         AI VIRTUAL MOUSE — HAND GESTURE CONTROL             ║
║         Math Utilities                                       ║
║         License : MIT — License-Free & Copyright-Free        ║
╚══════════════════════════════════════════════════════════════╝
"""

import math


# ══════════════════════════════════════════════════════════════
# BASIC GEOMETRY
# ══════════════════════════════════════════════════════════════

def distance(a: tuple, b: tuple) -> float:
    """
    Euclidean distance between two (x, y) pixel points.

        a, b → (x, y) tuples
        returns float distance
    """
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clamp(value: float, lo: float, hi: float) -> float:
    """
    Clamp *value* so it stays within [lo, hi].
    """
    return max(lo, min(value, hi))


# ══════════════════════════════════════════════════════════════
# HAND-AWARE DISTANCE
# ══════════════════════════════════════════════════════════════

def normalized_distance(
    coords: list,
    tip_a:  int,
    tip_b:  int,
) -> float:
    """
    Distance between two landmark tips, normalised by the
    wrist-to-middle-knuckle span (palm size).

    This makes the reading scale-invariant — it doesn't matter
    how close or far the hand is from the camera, or how large
    the user's hand is. A value below a threshold (e.g. 0.35)
    reliably signals a pinch.

    MediaPipe landmark indices used:
        coords[0]  = wrist
        coords[9]  = middle MCP knuckle  (palm reference)
        coords[N]  = whatever fingertip you pass in
    """
    palm_span = distance(coords[0], coords[9])
    if palm_span == 0:
        return 999.0                       # guard against division by zero
    return distance(coords[tip_a], coords[tip_b]) / palm_span
