"""Preprocessor usage example."""
from aiohttp import web

from aries_staticagent import StaticConnection, utils

from common import config

TYPE = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message"


def validate_basic_message(msg):
    """Validate basic messages.

    This example just uses basic assertions but you could easily use a schema
    library to get more sophisticated validators.
    """
    assert msg.type == TYPE
    assert '~l10n' in msg
    assert 'sent_time' in msg
    assert 'content' in msg
    msg['added_something'] = 'Something!'
    return msg


def main():
    """Create StaticConnection and start web server."""
    keys, target, args = config()
    conn = StaticConnection(keys, target)

    @conn.route(TYPE)
    @utils.validate(validate_basic_message)
    async def basic_message(msg, conn):
        """Respond to a basic message."""
        await conn.send_async({
            "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/"
                     "basicmessage/1.0/message",
            "~l10n": {"locale": "en"},
            "sent_time": utils.timestamp(),
            "content": (
                "The preprocessor validated this message and added: "
                "{}".format(msg['added_something'])
            )
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
