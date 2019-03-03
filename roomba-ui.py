#!/usr/bin/env python3

import curses
from curses import wrapper
from math import floor
from time import time, sleep
from pycreate2 import Create2

class RoombaController:
    def __init__(self, port='/dev/ttyUSB0', baud=115200):
        self.bot = Create2(port, baud=baud)
        self.bot.start()
        self.bot.full()
        self.bot.drive_stop()

    def __del__(self):
        del self.bot

def main(port='/dev/ttyUSB0', baud=115200):
    try:
        controller = RoombaController(port, baud)
        def curses_main(stdscr):
            stdscr.nodelay(True)
            while True:
                try:
                    key = stdscr.getkey()
                    if key == 'KEY_UP':
                        controller.bot.drive_straight(500)
                    elif key == 'KEY_DOWN':
                        controller.bot.drive_straight(-100)
                    elif key == 'KEY_LEFT':
                        controller.bot.drive_rotate(100, 1)
                    elif key == 'KEY_RIGHT':
                        controller.bot.drive_rotate(100, -1)
                    elif key == ' ':
                        controller.bot.drive_stop()
                except curses.error:
                    pass
        wrapper(curses_main)
    finally:
        pass

if __name__ == '__main__':
    main()
