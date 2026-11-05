#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         AI VIRTUAL MOUSE — HAND GESTURE CONTROL             ║
║         Configuration — All settings in one place           ║
║         License : MIT — License-Free & Copyright-Free        ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

# Always resolve resources relative to this file, not the working directory
PROJECT_ROOT = Path(__file__).resolve().parent


# ══════════════════════════════════════════════════════════════
# CAMERA
# ══════════════════════════════════════════════════════════════
@dataclass
class CameraConfig:
    INDEX:  int = int(os.environ.get("AI_VM_CAMERA_INDEX", "0") or 0)  # 0 = default webcam
    WIDTH: int = 640    # Capture width  (px)
    HEIGHT: int = 480     # Capture height (px)


# ══════════════════════════════════════════════════════════════
# MEDIAPIPE MODEL
# ══════════════════════════════════════════════════════════════
@dataclass
class ModelConfig:
    PATH:                       str   = str(PROJECT_ROOT / "hand_landmarker.task")
    MAX_HANDS:                  int   = 1
    MIN_DETECTION_CONFIDENCE:   float = 0.75
    MIN_PRESENCE_CONFIDENCE:    float = 0.75
    MIN_TRACKING_CONFIDENCE:    float = 0.75


# ══════════════════════════════════════════════════════════════
# CURSOR CONTROL
# ══════════════════════════════════════════════════════════════
@dataclass
class CursorConfig:
    SMOOTHING: float = 0.25   # 0.0 = frozen · 1.0 = raw (no smooth)
    MARGIN_X:  int   = 100    # Dead-zone pixels left & right
    MARGIN_Y:  int   = 80     # Dead-zone pixels top & bottom


# ══════════════════════════════════════════════════════════════
# GESTURE THRESHOLDS
# ══════════════════════════════════════════════════════════════
@dataclass
class GestureConfig:
    LEFT_CLICK_THRESHOLD:  float = 0.35   # Thumb ↔ Index distance
    RIGHT_CLICK_THRESHOLD: float = 0.35   # Thumb ↔ Middle distance
    DRAG_THRESHOLD:        float = 0.35   # Thumb ↔ Ring distance
    CLICK_COOLDOWN:        float = 0.45   # Seconds between clicks
    DRAG_START_DELAY:      float = 0.25   # Hold time before drag begins
    SCROLL_SPEED:          int   = 3      # Lines scrolled per tick
    VOLUME_MIN_DISTANCE: float = 0.20
    VOLUME_MAX_DISTANCE: float = 0.80
    VOLUME_SMOOTHING: float = 0.15
    VOLUME_ACTIVATION_DELAY: float = 0.70
    VOLUME_EXIT_DELAY: float = 0.60


# ══════════════════════════════════════════════════════════════
# USER INTERFACE  (all colours are BGR for OpenCV)
# ══════════════════════════════════════════════════════════════
@dataclass
class UIConfig:
    SHOW_LANDMARKS:    bool  = True
    SHOW_FPS:          bool  = True
    SHOW_GESTURE:      bool  = True
    SHOW_INSTRUCTIONS: bool  = True

    HEADER_BG:         Tuple = (20,  20,  20)
    LANDMARK_COLOR:    Tuple = (0,   255, 128)
    CONNECTION_COLOR:  Tuple = (0,   200,  80)
    TEXT_COLOR:        Tuple = (255, 255, 255)
    ACCENT_COLOR:      Tuple = (0,   255, 128)
    REGION_COLOR:      Tuple = (200, 200, 200)
    STATUS_OK:         Tuple = (0,   255, 128)
    STATUS_BAD:        Tuple = (0,    80, 255)


# ══════════════════════════════════════════════════════════════
# ROOT CONFIG OBJECT  (import this everywhere)
# ══════════════════════════════════════════════════════════════
@dataclass
class AppConfig:
    camera:  CameraConfig  = field(default_factory=CameraConfig)
    model:   ModelConfig   = field(default_factory=ModelConfig)
    cursor:  CursorConfig  = field(default_factory=CursorConfig)
    gesture: GestureConfig = field(default_factory=GestureConfig)
    ui:      UIConfig      = field(default_factory=UIConfig)


# ── Singleton used across the whole project ──────────────────
CONFIG = AppConfig()
