from enum import Enum


class Mode(Enum):
    NORMAL = "NORMAL"
    VOLUME = "VOLUME"
    BRIGHTNESS = "BRIGHTNESS"
    MEDIA = "MEDIA"
    PRESENTATION = "PRESENTATION"


class ModeManager:

    def __init__(self):
        self.mode = Mode.NORMAL

    def set_mode(self, mode):
        self.mode = mode

    def get_mode(self):
        return self.mode

    def is_mode(self, mode):
        return self.mode == mode