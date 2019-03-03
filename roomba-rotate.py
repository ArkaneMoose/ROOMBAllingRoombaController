#!/usr/bin/env python3

from math import floor
from time import time, sleep
from pycreate2 import Create2

STRAFE_SPEED = 100
STRAFE_CHANGE_DIRECTION_TIME = 1066.8 / 10 / STRAFE_SPEED
TILT_SPEED = 100
TILT_CHANGE_DIRECTION_TIME = 0.5

class RoombaController:
    def __init__(self, port='/dev/ttyUSB0', baud=115200):
        self.bot = Create2(port, baud=baud)
        self.bot.start()
        self.bot.full()
        self.bot.drive_stop()
        self._bumped = False

    def __del__(self):
        del self.bot

def main(port='/dev/ttyUSB0', baud=115200):
    try:
        controller = RoombaController(port, baud)
        controller.bot.drive_rotate(114, 1)
        sleep(6.47609012/4)
        controller.bot.drive_stop()
    finally:
        del controller

if __name__ == '__main__':
    main('/dev/ttyUSB0')
