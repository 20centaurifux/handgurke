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

def get_opts(argv):
    options, _ = getopt.getopt(argv, 's:p:n:g:SN', ["server=", "port=", "nick=", "group=", "ssl", "no-verify"])

    m = {"server": "internetcitizens.band", "ssl": False, "group": "", "verify_cert": True}

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

        if m:
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

    connection = await icb_client.connect()

    icb_client.login(opts["loginid"], opts["nick"], opts["group"])

    with ui.Ui() as stdscr:
        model = window.ViewModel()

        model.title = "Handgurke"

        w = window.Window(stdscr, model)

        skip_refresh = 0

        with ui.KeyReader(stdscr) as queue:
            icb_client.command("echoback", "verbose")
            icb_client.command("topic")

            client_f = asyncio.ensure_future(icb_client.read())
            input_f = asyncio.ensure_future(queue.get())
            sleep_f = asyncio.ensure_future(asyncio.sleep(1))

            group = ""
            topic = ""

            while not connection.done():
                if topic:
                    model.title = "%s: %s" % (group, topic)
                else:
                    model.title = group

                if skip_refresh == 0: # fixes resizing problems in some terminals, e.g. Terminator
                    w.refresh()
                else:
                    skip_refresh -= 1

                done, _ = await asyncio.wait([client_f, input_f, sleep_f], return_when=asyncio.FIRST_COMPLETED)

                for f in done:
                    if f is client_f:
                        message_type, fields = f.result()

                        if message_type == "l":
                            icb_client.pong()
                        elif message_type in "bcdefki":
                            model.append_message(datetime.now(), message_type, fields)

                            m = parse_message(message_type, fields)

                            group = m.get("group", group)
                            topic = m.get("topic", topic)

                        client_f = asyncio.ensure_future(icb_client.read())
                    elif f is input_f:
                        ch = f.result()

                        if ch == "\n":
                            line = model.text.strip()

                            if line == "/quit":
                                icb_client.quit()
                            else:
                                send_line(icb_client, line)

                            model.text = ""
                        else:
                            if ch == curses.KEY_RESIZE:
                                skip_refresh = 1

                            w.send_key(ch)

                        input_f = asyncio.ensure_future(queue.get())
                    elif f is sleep_f:
                        sleep_f = asyncio.ensure_future(asyncio.sleep(1))

if __name__ == "__main__":
    def signal_handler(sig, frame):
        pass

    signal.signal(signal.SIGINT, signal_handler)

    loop = asyncio.get_event_loop()

    loop.run_until_complete(run())

    print("Connection closed.")
