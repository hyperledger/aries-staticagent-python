"""Example return route capable agent."""

import hashlib
from aiohttp import web
from aries_staticagent import StaticConnection, crypto, utils


def main():
    """Start a server with a static connection."""
    keys = crypto.create_keypair(
        seed=hashlib.sha256(b'server').digest()
    )
    their_vk, _ = crypto.create_keypair(
        seed=hashlib.sha256(b'client').digest()
    )
    conn = StaticConnection(keys, their_vk=their_vk, endpoint=None)

    @conn.route('did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message')
    async def basic_message_auto_responder(msg, conn):
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
        with conn.reply_handler(response.append):
            await conn.handle(await request.read())

        if response:
            return web.Response(body=response.pop())

        raise web.HTTPAccepted()

    app = web.Application()
    app.add_routes([web.post('/', handle)])

    web.run_app(app, port=3000)


if __name__ == '__main__':
    main()
