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
import ltd

class ICBClientProtocol(asyncio.Protocol):
    def __init__(self, on_conn_lost, queue):
        self.__on_conn_lost = on_conn_lost
        self.__transport = None
        self.__decoder = ltd.Decoder()
        self.__decoder.add_listener(self.__message_received__)
        self.__queue = queue

    def connection_made(self, transport):
        self.__transport = transport

    def data_received(self, data):
        try:
            self.__decoder.write(data)

        except Exception as ex:
            self.__shutdown__(ex)

    def connection_lost(self, ex):
        self.__shutdown__(ex)

    def __shutdown__(self, ex=None):
        self.__on_conn_lost.set_result(ex)

    def __message_received__(self, type_id, payload):
        self.__queue.put_nowait((type_id, payload))

class Client:
    def __init__(self, host, port):
        self.__host = host
        self.__port = port
        self.__queue = asyncio.Queue()
        self.__transport = None

    async def connect(self):
        loop = asyncio.get_event_loop()

        on_conn_lost = loop.create_future()

        self.__transport, _ = await loop.create_connection(lambda: ICBClientProtocol(on_conn_lost, self.__queue),
                                                           self.__host,
                                                           self.__port)

        return on_conn_lost

    def login(self, loginid, nick, group="", password=""):
        e = ltd.Encoder("a")

        e.add_field_str(loginid)
        e.add_field_str(nick)
        e.add_field_str(group)
        e.add_field_str("login")
        e.add_field_str(password)

        self.__transport.write(e.encode())

    def open_message(self, text):
        self.__transport.write(ltd.encode_str("b", text.strip()))

    def command(self, command, arg=""):
        e = ltd.Encoder("h")

        e.add_field_str(command)
        e.add_field_str(arg if not arg is None else "")

        self.__transport.write(e.encode())

    def pong(self):
        self.__transport.write(ltd.encode_empty_cmd("m"))

    async def read(self):
        t, p = await self.__queue.get()

        if t == "g":
            self.__transport.close()

        return t, [f.decode("UTF-8").rstrip(" \0") for f in ltd.split(p)]
