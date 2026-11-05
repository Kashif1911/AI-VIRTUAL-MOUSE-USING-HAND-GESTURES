#!/usr/bin/env python3
"""Gesture detection and multi-mode control for AI Virtual Mouse Pro."""

import time
from enum import Enum
import math

from config import CONFIG
from utils.math_utils import normalized_distance
from modules.action_manager import ActionManager
from modules.mode_manager import ModeManager, Mode
from modules.brightness_controller import BrightnessController


class Gesture(Enum):
    NONE = "NONE"
    MOVE = "MOVE"
    LEFT_CLICK = "LEFT CLICK"
    RIGHT_CLICK = "RIGHT CLICK"
    DRAGGING = "DRAGGING"
    SCROLL_UP = "SCROLL UP"
    SCROLL_DOWN = "SCROLL DOWN"
    VOLUME = "VOLUME"
    BRIGHTNESS = "BRIGHTNESS"
    MEDIA = "MEDIA"


class GestureEngine:
    """Detect gestures, manage modes, and delegate OS actions."""

    def __init__(self):
        self.dragging = False
        self._drag_start = None

        self._last_click_time = 0.0
        self._last_rclick_time = 0.0

        self.action = ActionManager()
        self.mode = ModeManager()

        # =====================================================
        # VOLUME
        # =====================================================

        self.volume_percent = self.action.get_volume()
        self._smoothed_volume = float(self.volume_percent)

        self._volume_activation_start = None
        self._volume_last_seen = 0.0

        # =====================================================
        # BRIGHTNESS
        # =====================================================

        self.brightness = BrightnessController()

        self.brightness_percent = self.brightness.get_brightness()
        self._smoothed_brightness = float(
            self.brightness_percent
        )

        self._brightness_activation_start = None
        self._brightness_last_seen = 0.0

        # =====================================================
        # MEDIA
        # =====================================================

        self._media_activation_start = None
        self._last_media_action = 0.0
        # Media activation and media exit intentionally use the same
        # four-finger open-palm pose. After activation, require the hand
        # to leave the pose once before another palm can exit the mode.
        self._media_exit_armed = False

        # Prevent repeated media actions while pinching.
        self.MEDIA_ACTION_COOLDOWN = 0.8

    # =========================================================
    # BASIC FINGER DETECTION
    # =========================================================

    @staticmethod
    def _finger_extended(coords, tip, pip):
        return coords[tip][1] < coords[pip][1]
    @staticmethod
    def _thumb_extended(coords):
    # Thumb is considered extended when the thumb tip
    # is sufficiently far from the thumb MCP joint.
        thumb_distance = normalized_distance(coords, 4, 2)
        return thumb_distance > 0.55

    # =========================================================
    # VOLUME POSE
    # Index + Middle UP
    # Ring + Pinky DOWN
    # =========================================================

    def _volume_pose(self, coords):
        index_up = self._finger_extended(coords, 8, 6)
        middle_up = self._finger_extended(coords, 12, 10)
        ring_up = self._finger_extended(coords, 16, 14)
        pinky_up = self._finger_extended(coords, 20, 18)

        return (
            index_up
            and middle_up
            and not ring_up
            and not pinky_up
        )

    # =========================================================
    # BRIGHTNESS POSE
    # Index + Middle + Ring UP
    # Pinky DOWN
    # =========================================================

    def _brightness_pose(self, coords):
        index_up = self._finger_extended(coords, 8, 6)
        middle_up = self._finger_extended(coords, 12, 10)
        ring_up = self._finger_extended(coords, 16, 14)
        pinky_up = self._finger_extended(coords, 20, 18)

        return (
            index_up
            and middle_up
            and ring_up
            and not pinky_up
        )

    # =========================================================
    # PALM POSE
    # All four fingers UP
    # Used to EXIT Brightness / Media
    # =========================================================

    def _palm_pose(self, coords):
        index_up = self._finger_extended(coords, 8, 6)
        middle_up = self._finger_extended(coords, 12, 10)
        ring_up = self._finger_extended(coords, 16, 14)
        pinky_up = self._finger_extended(coords, 20, 18)

        thumb_distance = math.hypot(
            coords[4][0] - coords[5][0],
            coords[4][1] - coords[5][1]
        )

        palm_size = math.hypot(
            coords[0][0] - coords[9][0],
            coords[0][1] - coords[9][1]
        )

        thumb_up = thumb_distance > (0.75 * palm_size)

        return (
            index_up
            and middle_up
            and ring_up
            and pinky_up
            and thumb_up
        )
    # =========================================================
    # MEDIA ACTIVATION POSE
    #
    # =========================================================
# MEDIA ACTIVATION POSE
#
# Pinky UP only
# Index + Middle + Ring DOWN
#
# Hold to activate Media Mode.
# =========================================================
    
    # Hold to activate Media Mode. The same open-palm pose is
    # used to exit Media Mode after the hand has been released
    # from the activation pose once.
    # =========================================================

    def _media_pose(self, coords):
        index_up = self._finger_extended(coords, 8, 6)
        middle_up = self._finger_extended(coords, 12, 10)
        ring_up = self._finger_extended(coords, 16, 14)
        pinky_up = self._finger_extended(coords, 20, 18)

        # Media Mode:
        # Only Pinky finger should be UP.
        # Index, Middle and Ring fingers should be DOWN.
        return (
            pinky_up
            and not index_up
            and not middle_up
            and not ring_up
        )

    # =========================================================
    # ENTER VOLUME MODE
    # =========================================================

    def _enter_volume_if_requested(self, coords, now):
        activation_distance = normalized_distance(
            coords,
            4,
            8
        )

        pose_ok = (
            self._volume_pose(coords)
            and activation_distance > 0.45
        )

        if not pose_ok:
            self._volume_activation_start = None
            return False

        if self._volume_activation_start is None:
            self._volume_activation_start = now
            return False

        if (
            now - self._volume_activation_start
            >= CONFIG.gesture.VOLUME_ACTIVATION_DELAY
        ):
            self.mode.set_mode(Mode.VOLUME)

            self._volume_last_seen = now
            self._volume_activation_start = None

            print("[GESTURE] Volume Mode Activated")

            return True

        return False

    # =========================================================
    # ENTER BRIGHTNESS MODE
    # =========================================================

    def _enter_brightness_if_requested(self, coords, now):
        activation_distance = normalized_distance(
            coords,
            4,
            8
        )

        pose_ok = (
            self._brightness_pose(coords)
            and activation_distance > 0.45
        )

        if not pose_ok:
            self._brightness_activation_start = None
            return False

        if self._brightness_activation_start is None:
            self._brightness_activation_start = now
            return False

        if (
            now - self._brightness_activation_start
            >= CONFIG.gesture.VOLUME_ACTIVATION_DELAY
        ):
            self.mode.set_mode(Mode.BRIGHTNESS)

            self._brightness_last_seen = now
            self._brightness_activation_start = None

            print("[GESTURE] Brightness Mode Activated")

            return True

        return False

    # =========================================================
    # ENTER MEDIA MODE
    # =========================================================

    def _enter_media_if_requested(self, coords, now):
        # Media activation is the requested four-finger open palm.
        pose_ok = self._media_pose(coords)

        if not pose_ok:
            self._media_activation_start = None
            return False

        if self._media_activation_start is None:
            self._media_activation_start = now
            return False

        if (
            now - self._media_activation_start
            >= CONFIG.gesture.VOLUME_ACTIVATION_DELAY
        ):
            self.mode.set_mode(Mode.MEDIA)

            self._media_activation_start = None
            self._last_media_action = 0.0
            self._media_exit_armed = False

            print("[GESTURE] Media Mode Activated")

            return True

        return False

    # =========================================================
    # HANDLE VOLUME MODE
    # =========================================================

    def _handle_volume_mode(self, coords, now):

        if self._volume_pose(coords):

            self._volume_last_seen = now

            distance = normalized_distance(
                coords,
                4,
                8
            )

            d_min = CONFIG.gesture.VOLUME_MIN_DISTANCE
            d_max = CONFIG.gesture.VOLUME_MAX_DISTANCE

            ratio = (
                distance - d_min
            ) / max(
                d_max - d_min,
                1e-6
            )

            target = max(
                0.0,
                min(
                    100.0,
                    ratio * 100.0
                )
            )

            alpha = CONFIG.gesture.VOLUME_SMOOTHING

            self._smoothed_volume += (
                alpha
                * (
                    target
                    - self._smoothed_volume
                )
            )

            self.volume_percent = int(
                round(
                    self._smoothed_volume
                )
            )

            self.action.set_volume(
                self.volume_percent
            )

            return Gesture.VOLUME

        # Exit after pose disappears.
        if (
            now - self._volume_last_seen
            >= CONFIG.gesture.VOLUME_EXIT_DELAY
        ):
            self.mode.set_mode(Mode.NORMAL)

        return Gesture.VOLUME

    # =========================================================
    # HANDLE BRIGHTNESS MODE
    # =========================================================

    def _handle_brightness_mode(self, coords, now):

        # Palm exits brightness mode.
        if self._palm_pose(coords):

            print("[GESTURE] Exit Brightness Mode")

            self.mode.set_mode(Mode.NORMAL)

            return Gesture.MOVE

        if self._brightness_pose(coords):

            self._brightness_last_seen = now

            distance = normalized_distance(
                coords,
                4,
                8
            )

            d_min = CONFIG.gesture.VOLUME_MIN_DISTANCE
            d_max = CONFIG.gesture.VOLUME_MAX_DISTANCE

            ratio = (
                distance - d_min
            ) / max(
                d_max - d_min,
                1e-6
            )

            target = max(
                0.0,
                min(
                    100.0,
                    ratio * 100.0
                )
            )

            alpha = CONFIG.gesture.VOLUME_SMOOTHING

            self._smoothed_brightness += (
                alpha
                * (
                    target
                    - self._smoothed_brightness
                )
            )

            self.brightness_percent = int(
                round(
                    self._smoothed_brightness
                )
            )

            self.brightness.set_brightness(
                self.brightness_percent
            )

            return Gesture.BRIGHTNESS

        # Exit if pose disappears for a while.
        if (
            now - self._brightness_last_seen
            >= CONFIG.gesture.VOLUME_EXIT_DELAY
        ):
            self.mode.set_mode(Mode.NORMAL)

        return Gesture.BRIGHTNESS

    # =========================================================
    # HANDLE MEDIA MODE
    #
    # Thumb + Index  = Play/Pause
    # Thumb + Middle = Next Track
    # Thumb + Ring   = Previous Track
    # Palm           = Exit
    # =========================================================

    def _handle_media_mode(self, coords, now):

        # -----------------------------------------------------
        # Exit Media Mode with palm
        # -----------------------------------------------------

        if self._palm_pose(coords):
            # The activation gesture is also an open palm. Do not exit
            # immediately on the same held gesture; require one release
            # first, then a fresh open palm to exit.
            if self._media_exit_armed:
                print("[GESTURE] Exit Media Mode")
                self.mode.set_mode(Mode.NORMAL)
                self._media_exit_armed = False
                return Gesture.MOVE
            return Gesture.MEDIA

        # Once the hand leaves the activation palm, the next open palm
        # becomes a valid exit gesture.
        self._media_exit_armed = True

        # Prevent repeated actions.
        if (
            now - self._last_media_action
            < self.MEDIA_ACTION_COOLDOWN
        ):
            return Gesture.MEDIA

        # -----------------------------------------------------
        # Play / Pause
        # Thumb + Index
        # -----------------------------------------------------

        d_play = normalized_distance(
            coords,
            4,
            8
        )

        if (
            d_play
            < CONFIG.gesture.LEFT_CLICK_THRESHOLD
        ):
            self.action.media_play_pause()

            self._last_media_action = now

            print("[MEDIA] Play/Pause")

            return Gesture.MEDIA

        # -----------------------------------------------------
        # Next Track
        # Thumb + Middle
        # -----------------------------------------------------

        d_next = normalized_distance(
            coords,
            4,
            12
        )

        if (
            d_next
            < CONFIG.gesture.RIGHT_CLICK_THRESHOLD
        ):
            self.action.media_next_track()

            self._last_media_action = now

            print("[MEDIA] Next Track")

            return Gesture.MEDIA

        # -----------------------------------------------------
        # Previous Track
        # Thumb + Ring
        # -----------------------------------------------------

        d_previous = normalized_distance(
            coords,
            4,
            16
        )

        if (
            d_previous
            < CONFIG.gesture.DRAG_THRESHOLD
        ):
            self.action.media_previous_track()

            self._last_media_action = now

            print("[MEDIA] Previous Track")

            return Gesture.MEDIA

        return Gesture.MEDIA

    # =========================================================
    # MAIN GESTURE DETECTION
    # =========================================================

    def detect(self, coords: list) -> Gesture:

        now = time.time()

        # -----------------------------------------------------
        # Active modes
        # -----------------------------------------------------

        if self.mode.is_mode(Mode.VOLUME):
            return self._handle_volume_mode(
                coords,
                now
            )

        if self.mode.is_mode(Mode.BRIGHTNESS):
            return self._handle_brightness_mode(
                coords,
                now
            )

        if self.mode.is_mode(Mode.MEDIA):
            return self._handle_media_mode(
                coords,
                now
            )

        # -----------------------------------------------------
        # Mode activation
        # -----------------------------------------------------

        if self._enter_volume_if_requested(
            coords,
            now
        ):
            return Gesture.VOLUME

        if self._enter_brightness_if_requested(
            coords,
            now
        ):
            return Gesture.BRIGHTNESS

        if self._enter_media_if_requested(
            coords,
            now
        ):
            return Gesture.MEDIA

        # -----------------------------------------------------
        # Left Click
        # Thumb + Index
        # -----------------------------------------------------

        d_left = normalized_distance(
            coords,
            4,
            8
        )

        if (
            d_left
            < CONFIG.gesture.LEFT_CLICK_THRESHOLD
        ):
            if (
                now - self._last_click_time
                > CONFIG.gesture.CLICK_COOLDOWN
            ):

                self._last_click_time = now

                self.action.left_click()

                return Gesture.LEFT_CLICK

        # -----------------------------------------------------
        # Right Click
        # Thumb + Middle
        # -----------------------------------------------------

        d_right = normalized_distance(
            coords,
            4,
            12
        )

        if (
            d_right
            < CONFIG.gesture.RIGHT_CLICK_THRESHOLD
        ):
            if (
                now - self._last_rclick_time
                > CONFIG.gesture.CLICK_COOLDOWN
            ):

                self._last_rclick_time = now

                self.action.right_click()

                return Gesture.RIGHT_CLICK

        # -----------------------------------------------------
        # Drag
        # Thumb + Ring
        # -----------------------------------------------------

        d_drag = normalized_distance(
            coords,
            4,
            16
        )

        if (
            d_drag
            < CONFIG.gesture.DRAG_THRESHOLD
        ):

            if self._drag_start is None:
                self._drag_start = now

            if (
                not self.dragging
                and now - self._drag_start
                > CONFIG.gesture.DRAG_START_DELAY
            ):
                self.dragging = True

                self.action.mouse_down()

            return Gesture.DRAGGING

        self._drag_start = None

        if self.dragging:

            self.action.mouse_up()

            self.dragging = False

        
        # -----------------------------------------------------
        # Scroll
        # Thumbs Up = Scroll Up
        # Thumbs Down = Scroll Down
        # -----------------------------------------------------

        thumb_tip_y = coords[4][1]
        thumb_joint_y = coords[3][1]
        thumb_base_y = coords[2][1]

        index_extended = self._finger_extended(
            coords, 8, 6
        )

        middle_extended = self._finger_extended(
            coords, 12, 10
        )

        ring_extended = self._finger_extended(
            coords, 16, 14
        )

        pinky_extended = self._finger_extended(
            coords, 20, 18
        )

        thumb_up = (
            thumb_tip_y < thumb_joint_y
            and thumb_joint_y < thumb_base_y
        )

        thumb_down = (
            thumb_tip_y > thumb_joint_y
            and thumb_joint_y > thumb_base_y
        )

        other_fingers_folded = (
            not index_extended
            and not middle_extended
            and not ring_extended
            and not pinky_extended
        )

        if other_fingers_folded and thumb_up:
            self.action.scroll_up(
                CONFIG.gesture.SCROLL_SPEED
            )
            return Gesture.SCROLL_UP

        if other_fingers_folded and thumb_down:
            self.action.scroll_down(
                CONFIG.gesture.SCROLL_SPEED
            )
            return Gesture.SCROLL_DOWN

        return Gesture.MOVE
