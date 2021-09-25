"""Webserver with websockets example."""

import aiohttp
from aiohttp import web

from aries_staticagent import Connection, utils

from common import config


def main():
    """Create Connection and start web server."""
    keys, target, args = config()
    conn = Connection(keys, target)

    @conn.route("https://didcomm.org/basicmessage/1.0/message")
    async def basic_message(msg, conn):
        """Respond to a basic message."""
        await conn.send_async(
            {
                "@type": "https://didcomm.org/" "basicmessage/1.0/message",
                "~l10n": {"locale": "en"},
                "sent_time": utils.timestamp(),
                "content": "You said: {}".format(msg["content"]),
            }
        )

    async def ws_handle(request):
        """Handle WS requests."""
        sock = web.WebSocketResponse()
        await sock.prepare(request)

        with conn.session(sock.send_bytes) as session:
            async for msg in sock:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    await session.handle(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print("ws connection closed with exception %s" % sock.exception())

                if not session.should_return_route():
                    await sock.close()

        return sock

    async def post_handle(request):
        """Handle posted messages."""
        response = []
        with conn.session(response.append) as session:
            await session.handle(await request.read())

        if response:
            return web.Response(text=response.pop())

        raise web.HTTPAccepted()

    app = web.Application()
    app.add_routes([web.get("/", ws_handle), web.post("/", post_handle)])

    web.run_app(app, port=args.port)


if __name__ == "__main__":
    main()
