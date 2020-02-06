"""Webserver example."""
from aiohttp import web

from aries_staticagent import StaticConnection, utils

from common import config

def main():
    """Create StaticConnection and start web server."""
    args = config()
    conn = StaticConnection(
        (args.my_verkey, args.my_sigkey),
        their_vk=args.their_verkey,
        endpoint=args.endpoint,
    )

    @conn.route("did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message")
    async def basic_message(msg, conn):
        """Respond to a basic message."""
        await conn.send_async({
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/"
                     "basicmessage/1.0/message",
            "~l10n": {"locale": "en"},
            "sent_time": utils.timestamp(),
            "content": "You said: {}".format(msg['content'])
        })

    async def handle(request):
        """aiohttp handle POST."""
        response = []
        with conn.session(response.append) as session:
            await conn.handle(await request.read(), session)

        if response:
            return web.Response(text=response.pop())

        raise web.HTTPAccepted()

    app = web.Application()
    app.add_routes([web.post('/', handle)])

    web.run_app(app, port=args.port)


if __name__ == '__main__':
    main()
