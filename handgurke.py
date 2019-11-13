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
from datetime import datetime
import re
import getopt
import getpass
import signal
import sys
import curses
import ui
import window
import client
import timer
import beat

def get_opts(argv):
    options, _ = getopt.getopt(argv, 's:p:n:g:SNM', ["server=", "port=", "nick=", "group=", "ssl", "no-verify", "enable-mouse"])

    m = {"server": "internetcitizens.band", "ssl": False, "group": "", "verify_cert": True, "mouse": False}

    for opt, arg in options:
        if opt in ('-s', '--server'):
            m["server"] = arg
        elif opt in ('-p', '--port'):
            m["port"] = int(arg)
        elif opt in ('-n', '--nick'):
            m["nick"] = arg
        elif opt in ('-g', '--group'):
            m["group"] = arg
        elif opt in ('-S', '--ssl'):
            m["ssl"] = True
        elif opt in ('-N', '--no-verify'):
            m["verify_cert"] = False
        elif opt in ('-M', '--enable-mouse'):
            m["mouse"] = True

    if not "port" in m:
        m["port"] = 7327 if m["ssl"] else 7326

    m["loginid"] = getpass.getuser()

    if not m.get("nick"):
        m["nick"] = m["loginid"]

    return m

def parse_message(message_type, fields):
    result = {}

    if message_type == "d" and fields[0] == "Status":
        m = re.match(r"^You are now in group ([^\s]+).*", fields[1])

        if m:
            result["group"] = m.group(1)
            result["topic"] = ""
    if message_type == "d" and fields[0] == "Topic":
        m = re.match(r".*changed the topic to \"([\s\w]+)\".*", fields[1])

        if m and m.group(1) != "(None)":
            result["topic"] = m.group(1)
    elif message_type == "i" and fields[0] == "co":
        m = re.match(r".*Topic: (.*)$", fields[1])

        if not m:
            m = re.match(r".*The topic is: (.*)$", fields[1])

        if m and m.group(1) != "(None)":
            result["topic"] = m.group(1)

    return result

def send_line(client, line):
    if line.startswith("/"):
        parts = line.split(" ", 1)

        if len(parts[0]) > 1:
            client.command(parts[0][1:], parts[1] if len(parts) > 1 else "")

        if parts[0] == "/g" and len(parts) == 2:
            client.command("topic")
    else:
        client.open_message(line)

async def run():
    opts = get_opts(sys.argv[1:])

    icb_client = client.Client(opts["server"], opts["port"], use_ssl=opts["ssl"], verify_cert=opts["verify_cert"])

    with ui.Ui(mouse=opts["mouse"]) as stdscr:
        model = window.ViewModel()

        w = window.Window(stdscr, model)

        with ui.KeyReader(stdscr) as queue:
            connection_f = asyncio.ensure_future(asyncio.sleep(0))
            client_f = asyncio.ensure_future(icb_client.read())
            input_f = asyncio.ensure_future(queue.get())
            timer_f = asyncio.ensure_future(asyncio.sleep(0))

            last_login_attempt = None

            group = ""
            topic = ""

            quit = False

            while not quit:
                if topic:
                    model.title = "%s: %s" % (group, topic)
                else:
                    model.title = group

                w.refresh()

                done, _ = await asyncio.wait([client_f, input_f, timer_f, connection_f], return_when=asyncio.FIRST_COMPLETED)

                for f in done:
                    if f is connection_f:
                        if not last_login_attempt or last_login_attempt.elapsed() >= 10.0:
                            last_login_attempt = timer.Timer()

                            model.append_message(datetime.now(), "d", ["Connection", "Connecting to %s:%d..." % (opts["server"], opts["port"])])

                            connection_f = None

                            try:
                                connection_f = await icb_client.connect()

                                icb_client.login(opts["loginid"], opts["nick"], group if group else opts["group"])

                                icb_client.command("echoback", "verbose")
                                icb_client.command("topic")

                            except Exception as e:
                                model.append_message(datetime.now(), "e", [str(e)])

                            if not connection_f:
                                model.append_message(datetime.now(), "d", ["Connection", "Reconnecting in 10 seconds..."])
                                connection_f = asyncio.ensure_future(asyncio.sleep(10))
                    elif f is client_f:
                        msg = f.result()

                        if msg:
                            message_type, fields = msg

                            if message_type == "l":
                                icb_client.pong()
                            elif message_type in "bcdefki":
                                model.append_message(datetime.now(), message_type, fields)

                                m = parse_message(message_type, fields)

                                group = m.get("group", group)
                                topic = m.get("topic", topic)
                        else:
                            model.append_message(datetime.now(), "e", ["Connection timeout"])

                        client_f = asyncio.ensure_future(icb_client.read())
                    elif f is input_f:
                        ch = f.result()

                        if ch == "\n":
                            line = model.text.strip()

                            if line == "/quit":
                                try:
                                    icb_client.quit()
                                except: pass

                                quit = True
                            else:
                                try:
                                    send_line(icb_client, line)
                                except: pass

                            model.text = ""
                        else:
                            if ch == curses.KEY_RESIZE:
                                w.clear()

                            w.send_key(ch)

                        input_f = asyncio.ensure_future(queue.get())
                    elif f is timer_f:
                        model.time = beat.now()
                        timer_f = asyncio.ensure_future(asyncio.sleep(1))

if __name__ == "__main__":
    def signal_handler(sig, frame):
        pass

    signal.signal(signal.SIGINT, signal_handler)

    loop = asyncio.get_event_loop()

    loop.run_until_complete(run())
