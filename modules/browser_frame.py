#!/usr/bin/env python3
"""
Shared browser-camera frame buffer.

The Flask process writes the newest browser frame into shared memory.
The AI engine process reads the newest frame from the same buffer.
No image files are written to disk.
"""

import struct
import time
from multiprocessing import shared_memory

import cv2
import numpy as np


class BrowserFrameBuffer:
    WIDTH = 480
    HEIGHT = 360
    CHANNELS = 3

    _MAGIC = b"AIVM"
    _HEADER_SIZE = 64
    _SLOT_COUNT = 2
    _FRAME_BYTES = WIDTH * HEIGHT * CHANNELS
    SIZE = _HEADER_SIZE + (_SLOT_COUNT * _FRAME_BYTES)
    NAME = "AI_VIRTUAL_MOUSE_BROWSER_FRAME"

    # magic, width, height, channels, active_slot, sequence
    _HEADER = struct.Struct("<4sIIIIQ")

    def __init__(self, create=False):
        self._owner = False
        try:
            if create:
                try:
                    self._shm = shared_memory.SharedMemory(
                        name=self.NAME,
                        create=True,
                        size=self.SIZE,
                    )
                    self._owner = True
                    self._shm.buf[:] = b"\x00" * self.SIZE
                except FileExistsError:
                    self._shm = shared_memory.SharedMemory(
                        name=self.NAME,
                        create=False,
                    )
            else:
                self._shm = shared_memory.SharedMemory(
                    name=self.NAME,
                    create=False,
                )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Browser Vision shared frame buffer is not available. "
                "Start the Flask dashboard before starting Browser Vision."
            ) from exc

        self._sequence = self._read_header()[5]

    def _read_header(self):
        return self._HEADER.unpack_from(self._shm.buf, 0)

    def clear(self):
        self._HEADER.pack_into(
            self._shm.buf,
            0,
            self._MAGIC,
            self.WIDTH,
            self.HEIGHT,
            self.CHANNELS,
            0,
            0,
        )
        self._sequence = 0

    def write(self, frame):
        if frame is None:
            return False

        if frame.shape[1] != self.WIDTH or frame.shape[0] != self.HEIGHT:
            frame = cv2.resize(
                frame,
                (self.WIDTH, self.HEIGHT),
                interpolation=cv2.INTER_AREA,
            )

        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)

        if not frame.flags["C_CONTIGUOUS"]:
            frame = np.ascontiguousarray(frame)

        header = self._read_header()
        sequence = int(header[5]) + 1
        slot = sequence % self._SLOT_COUNT

        start = self._HEADER_SIZE + (slot * self._FRAME_BYTES)
        end = start + self._FRAME_BYTES
        self._shm.buf[start:end] = frame.reshape(-1).tobytes()

        self._HEADER.pack_into(
            self._shm.buf,
            0,
            self._MAGIC,
            self.WIDTH,
            self.HEIGHT,
            self.CHANNELS,
            slot,
            sequence,
        )
        return True

    def read_latest(self, last_sequence=0, timeout=0.10):
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            header = self._read_header()
            sequence = int(header[5])

            if sequence <= last_sequence:
                time.sleep(0.002)
                continue

            slot = int(header[4])
            start = self._HEADER_SIZE + (slot * self._FRAME_BYTES)
            end = start + self._FRAME_BYTES

            frame = np.frombuffer(
                self._shm.buf[start:end],
                dtype=np.uint8,
            ).reshape(
                self.HEIGHT,
                self.WIDTH,
                self.CHANNELS,
            ).copy()

            # Confirm the writer did not publish a newer frame while
            # we were copying this slot.
            if int(self._read_header()[5]) == sequence:
                self._sequence = sequence
                return frame, sequence

        return None, last_sequence

    @property
    def sequence(self):
        return self._sequence

    def close(self):
        if getattr(self, "_shm", None) is not None:
            self._shm.close()

    def unlink(self):
        if getattr(self, "_shm", None) is not None and self._owner:
            try:
                self._shm.unlink()
            except FileNotFoundError:
                pass
