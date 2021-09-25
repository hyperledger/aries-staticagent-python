"""Webserver example."""
from aiohttp import web

from aries_staticagent import StaticConnection, utils

from common import config


def main():
    """Create StaticConnection and start web server."""
    keys, target, args = config()
    conn = StaticConnection(keys, target)

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

    async def handle(request):
        """aiohttp handle POST."""
        response = []
        with conn.session(response.append) as session:
            await conn.handle(await request.read(), session)

        if response:
            return web.Response(text=response.pop())

        raise web.HTTPAccepted()

    app = web.Application()
    app.add_routes([web.post("/", handle)])

    web.run_app(app, port=args.port)


if __name__ == "__main__":
    main()
