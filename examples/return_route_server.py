"""Example return route capable agent.

This example is intended to be run with the return_route_client to demonstrate
return routing.
"""

import hashlib
import os
from aiohttp import web
from aries_staticagent import StaticConnection, Target, crypto, utils


def main():
    """Start a server with a static connection."""
    their_vk, _ = crypto.create_keypair(seed=hashlib.sha256(b"client").digest())
    conn = StaticConnection.from_seed(
        hashlib.sha256(b"server").digest(), Target(their_vk=their_vk)
    )

    @conn.route("https://didcomm.org/basicmessage/1.0/message")
    async def basic_message_auto_responder(msg, conn):
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
            return web.Response(body=response.pop())

        raise web.HTTPAccepted()

    app = web.Application()
    app.add_routes([web.post("/", handle)])

    web.run_app(app, port=os.environ.get("PORT", 3000))


if __name__ == "__main__":
    main()
