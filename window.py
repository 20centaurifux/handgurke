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
import curses
from textwrap import wrap
from datetime import datetime
import ui

class ViewModel:
    def __init__(self):
        self.__title = (False, "")
        self.__text = (False, "")
        self.__messages = []
        self.__message_count = 0

    @property
    def title(self):
        return self.__title[1]

    @title.setter
    def title(self, value):
        if value != self.__title[1]:
            self.__title = (True, value)

    @property
    def title_changed(self):
        return self.__title[0]
 
    @property
    def text(self):
        return self.__text[1]

    @text.setter
    def text(self, value):
        if value != self.__text[1]:
            self.__text = (True, value)

    @property
    def text_changed(self):
        return self.__text[0]

    @property
    def messages(self):
        return self.__messages

    def append_message(self, timestamp, message_type, fields):
        self.__messages.append((timestamp, message_type, fields))

    @property
    def messages_changed(self):
        return self.__message_count != len(self.__messages)

    @property
    def changed(self):
        return self.title_changed or self.text_changed or self.messages_changed

    def sync(self):
        self.__title = (False, self.__title[1])
        self.__text = (False, self.__text[1])
        self.__message_count = len(self.__messages)

class Window:
    def __init__(self, stdscr, model: ViewModel):
        self.__model = model
        self.__stdscr = stdscr
        self.__draw_screen = True
        self.__text_pos = 0
        self.__text_offset = 0
        self.__display_lines = 0
        self.__next_line = 0
        self.__scroll_to = -1

    @property
    def model(self):
        return self.__model

    def send_key(self, ch):
        if isinstance(ch, int):
            if ch == curses.KEY_RESIZE:
                self.__draw_screen = True
            elif ch in ["\b", 127, curses.KEY_BACKSPACE]:
                self.__backspace__()
            elif ch == curses.KEY_DC:
                self.__delete_char__()
            elif ch == curses.KEY_LEFT:
                self.__move_left__()
            elif ch == curses.KEY_RIGHT:
                self.__move_right__()
            elif ch == curses.KEY_HOME:
                self.__move_home__()
            elif ch == curses.KEY_END:
                self.__move_end__()
            elif ch == curses.KEY_PPAGE:
                self.__scroll_previous()
            elif ch == curses.KEY_NPAGE:
                self.__scroll_next()
        else:
            if ch == "\u007f":
                self.__backspace__()
            else:
                key_name = curses.keyname(ord(ch)).decode("UTF-8")

                if key_name == "^A":
                    self.__move_home__()
                elif key_name == "^E":
                    self.__move_end__()
                elif key_name == "^W":
                    self.__delete_word__()
                elif ord(ch) != 0:
                    self.__insert_char__(ch)

    def __backspace__(self):
        index = self.__text_offset + self.__text_pos

        if index > 0:
            self.__model.text = "%s%s" % (self.__model.text[:index - 1], self.__model.text[index:])

            if self.__text_pos == self.__x - 1 and self.__text_offset < 0:
                self.__text_offset += 1
            else:
                self.__text_pos -= 1

        self.__refresh_bottom__(force=True)

        self.__model.sync()

    def __delete_char__(self):
        index = self.__text_offset + self.__text_pos

        if index < len(self.__model.text):
            self.__model.text = "%s%s" % (self.__model.text[:index], self.__model.text[index + 1:])

    def __insert_char__(self, ch):
        text = self.__model.text
        split = self.__text_offset + self.__text_pos

        self.__model.text = "%s%s%s" % (text[:split], ch, text[split:])

        if self.__text_pos == self.__x - 1:
            self.__text_offset += 1
        else:
            self.__text_pos += 1

        self.__refresh_bottom__(force=True)

        self.__model.sync()

    def __delete_word__(self):
        index = self.__text_offset + self.__text_pos

        if index > 0:
            text = self.__model.text

            match = text.rfind(" ", 0, index - 1)

            if match == 0:
                self.__model.text = ""
                self.__text_pos = 0
                self.__text_offset = 0
            else:
                self.__model.text = "%s%s" % (text[:match + 1], text[index:])

                diff = len(text) - len(self.__model.text)

                self.__text_pos -= diff

                if len(self.__model.text) < self.__x - 1:
                    self.__text_pos += self.__text_offset
                    self.__text_offset = 0

            self.__refresh_bottom__(force=True)

            self.__model.sync()

    def __move_left__(self):
        if self.__text_pos > 0:
            self.__text_pos -= 1
            self.__bottom.move(0, self.__text_pos)
            self.__bottom.refresh()
        elif self.__text_offset > 0:
            self.__text_offset -= 1
            self.__refresh_bottom__(force=True)

    def __move_right__(self):
        if self.__text_pos + self.__text_offset < len(self.__model.text):
            if self.__text_pos < self.__x - 1:
                self.__text_pos += 1
                self.__bottom.move(0, self.__text_pos)
                self.__bottom.refresh()
            else:
                self.__text_offset += 1
                self.__refresh_bottom__(force=True)

    def __move_home__(self):
        self.__text_pos = 0
        self.__text_offset = 0
        self.__bottom.move(0, 0)
        self.__refresh_bottom__(force=True)

    def __move_end__(self):
        self.__text_pos = len(self.__model.text)

        if self.__text_pos > self.__x:
            self.__text_offset = self.__text_pos - self.__x + 1
            self.__text_pos = self.__x - 1
        else:
            self.__text_offset = 0

        self.__bottom.move(0, self.__text_pos)
        self.__refresh_bottom__(force=True)

    def __scroll_previous(self):
        pass

    def __scroll_next(self):
        pass

    def refresh(self):
        force = self.__draw_screen

        self.__create_screen__()

        refreshed = self.__refresh_top__(force)

        if self.__refresh_lines__(force):
            refreshed = True

        if refreshed:
            force = True

        self.__refresh_bottom__(force)

        self.__model.sync()

    def __create_screen__(self):
        if self.__draw_screen:
            self.__stdscr.erase()
            self.__stdscr.clear()
            self.__stdscr.refresh()

            y, x = self.__stdscr.getmaxyx()

            self.__y = y
            self.__x = x

            self.__top = curses.newwin(1, self.__x, 0, 0)
            self.__top.bkgd(' ', curses.color_pair(ui.COLORS_TITLE_BAR))

            self.__lines = curses.newpad(20, self.__x)
            self.__lines.bkgd(' ', curses.color_pair(ui.COLORS_MESSAGE))
            self.__display_lines = 0
            self.__next_line = 0

            self.__bottom = curses.newwin(1, self.__x, self.__y - 1, 0)
            self.__bottom.bkgd(' ', curses.color_pair(ui.COLORS_INPUT))

            self.__draw_screen = False

    def __refresh_top__(self, force):
        refreshed = False

        if self.__model.title_changed or force:
            refreshed = True

            self.__top.clear()

            title = self.__model.title

            if len(title) > self.__x - 16:
                title = "%s..." % title[:self.__x - 10]

            self.__top.addstr(0, 0, title)
            self.__top.refresh()

        return refreshed

    def __refresh_lines__(self, force):
        refreshed = False

        if self.__model.messages_changed or force:
            refreshed = True

            max_y, max_x = self.__lines.getmaxyx()

            for timestamp, message_type, fields in self.__model.messages[self.__next_line:]:
                if self.__display_lines >= max_y:
                    max_y *= 2
                    self.__lines.resize(max_y, max_x)

                padding = self.__write_prefix__(self.__display_lines, timestamp, message_type, fields)
                first_line = True

                colors = ui.COLORS_MESSAGE

                if message_type == "i":
                    colors = ui.COLORS_OUTPUT

                for l in self.__convert_message__(self.__x - padding, message_type, fields):
                    if self.__display_lines >= max_y:
                        max_y *= 2
                        self.__lines.resize(max_y, max_x)

                    if first_line: 
                        self.__lines.addstr(l, curses.color_pair(colors))
                        first_line = False
                    else:
                        self.__lines.addstr(self.__display_lines, 0, " " * padding, ui.COLORS_MESSAGE)
                        self.__lines.addstr(l, curses.color_pair(colors))

                    self.__display_lines += 1

                self.__next_line += 1

            if self.__scroll_to == -1:
                scroll_to = self.__display_lines - self.__y + 2 - self.__scroll_to

                self.__lines.refresh(scroll_to, 0, 1, 0, self.__y - 2, self.__x)
            else:
                self.__lines.refresh(self.__scroll_to, 0, 1, 0, self.__y - 2, self.__x)

        return refreshed

    def __write_prefix__(self, row, timestamp, message_type, fields):
        length = 9

        time = timestamp.strftime("%H:%M:%S")

        self.__lines.addstr(row, 0, time, curses.color_pair(ui.COLORS_TIMESTAMP))
        self.__lines.addstr(" ", curses.color_pair(ui.COLORS_MESSAGE))

        if message_type == "b":
            length += len(fields[0]) + 3
            self.__lines.addstr("<%s>" % fields[0], curses.color_pair(ui.COLORS_NICK))
            self.__lines.addstr(" ", curses.color_pair(ui.COLORS_MESSAGE))
        elif message_type == "c":
            length += len(fields[0]) + 3
            self.__lines.addstr("*%s*" % fields[0], curses.color_pair(ui.COLORS_PERSONAL) | curses.A_BOLD)
            self.__lines.addstr(" ", curses.color_pair(ui.COLORS_MESSAGE))
        elif message_type == "d":
            length += len(fields[0]) + 3
            self.__lines.addstr("[%s]" % fields[0], curses.color_pair(ui.COLORS_STATUS))
            self.__lines.addstr(" ", curses.color_pair(ui.COLORS_MESSAGE))
        elif message_type == "e":
            length += 6
            self.__lines.addstr("*ERR*", curses.color_pair(ui.COLORS_ERROR))
            self.__lines.addstr(" ", curses.color_pair(ui.COLORS_MESSAGE))
        elif message_type == "f":
            length += len(fields[0]) + 3
            self.__lines.addstr("[%s]" % fields[0], curses.color_pair(ui.COLORS_IMPORTANT))
            self.__lines.addstr(" ", curses.color_pair(ui.COLORS_MESSAGE))
        elif message_type == "k":
            length += 7
            self.__lines.addstr("*BEEP*", curses.color_pair(ui.COLORS_PERSONAL) | curses.A_BOLD)
            self.__lines.addstr(" ", curses.color_pair(ui.COLORS_MESSAGE))

        return length

    def __convert_message__(self, max_length, message_type, fields):
        lines = []

        if message_type in "bcdf":
            lines = wrap(fields[1], max_length)
        elif message_type == "e":
            lines = wrap(fields[0], max_length)
        elif message_type == "k":
            lines = ["%s beeps you." % fields[0]]
        elif message_type == "i":
            if fields[0] == "co":
                lines = wrap(fields[1], max_length)
            elif fields[0] == "wl":
                status = fields[8]

                if status:
                    status = " %s" % status

                l = " %1s %-16s %4s %-8s %s@%s%s" % (fields[1],
                                                     fields[2],
                                                     self.__idle_str__(int(fields[3])),
                                                     datetime.fromtimestamp(int(fields[5])).strftime("%X"),
                                                     fields[6],
                                                     fields[7],
                                                     status)
                lines = wrap(l, max_length)

        return lines

    @staticmethod
    def __idle_str__(elapsed):
        total_seconds = int(elapsed)
        total_minutes = int(total_seconds / 60)
        total_hours = int(total_minutes / 60)
        minutes = total_minutes - (total_hours * 60)

        parts = []

        if total_hours > 23:
            days = int(total_hours / 24)

            parts.append("%dd" % days)

            hours = total_hours - (days * 24)

            if hours > 0:
                parts.append("%dh" % hours)

            if minutes > 0:
                parts.append("%dm" % minutes)
        elif total_hours > 0:
            parts.append("%dh" % total_hours)

            if minutes > 0:
                parts.append("%dm" % minutes)
        elif total_minutes > 0:
            parts.append("%dm" % minutes)
        else:
            parts.append("%ds" % total_seconds)

        return "".join(parts)

    def __refresh_bottom__(self, force):
        if self.__model.text_changed or force:
            text = self.__model.text[self.__text_offset:]
            text = text[:self.__x - 1]

            text_len = len(text)

            text = text + " " * (self.__x - len(text) - 1)

            self.__bottom.addstr(0, 0, text)

            if self.__text_pos + self.__text_offset > text_len:
                self.__text_offset = 0
                self.__text_pos = text_len

            self.__bottom.move(0, self.__text_pos)

            self.__bottom.refresh()
