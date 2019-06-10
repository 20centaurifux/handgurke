"""
    project............: Handgurke
    description........: ICB client
    date...............: 06/2019
    copyright..........: Sebastian Fedrau

    Permission is hereby granted, free of charge, to any person obtaining
    a copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to
    the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
    IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
    OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    OTHER DEALINGS IN THE SOFTWARE.
"""
import asyncio
import threading
import curses

COLORS_TITLE_BAR = 1
COLORS_MESSAGE = 2
COLORS_INPUT = 3
COLORS_TIMESTAMP = 4
COLORS_NICK = 5
COLORS_PERSONAL = 6
COLORS_STATUS = 7
COLORS_ERROR = 8
COLORS_IMPORTANT = 9
COLORS_OUTPUT = 10

class Ui:
    def __enter__(self):
        self.__stdscr = curses.initscr()

        curses.noecho()

        self.__stdscr.keypad(True)
        self.__stdscr.nodelay(True)

        curses.start_color()

        curses.init_pair(COLORS_TITLE_BAR, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(COLORS_MESSAGE, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(COLORS_INPUT, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(COLORS_TIMESTAMP, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(COLORS_NICK, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(COLORS_PERSONAL, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(COLORS_STATUS, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(COLORS_ERROR, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(COLORS_IMPORTANT, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(COLORS_OUTPUT, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        return self.__stdscr

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__stdscr.keypad(False)
        curses.echo()

        curses.endwin()

class KeyReader:
    def __init__(self, stdscr):
        self.__loop = asyncio.get_event_loop()
        self.__stdscr = stdscr
        self.__worker = threading.Thread(target=self.__read_char__)
        self.__queue = asyncio.Queue()
        self.__event = threading.Event()

    def __enter__(self):
        self.__worker.start()

        return self.__queue

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__event.set()
        self.__worker.join()

    def __read_char__(self):
        while not self.__event.isSet():
            try:
                c = self.__stdscr.get_wch()
                self.__loop.call_soon_threadsafe(self.__queue.put_nowait, c)
            except: pass
