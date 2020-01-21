"""Webserver with module example."""
from aiohttp import web

from aries_staticagent import StaticConnection, Module, route, utils

from common import config


class BasicMessageCounter(Module):
    """A simple BasicMessage module.

    Responds with the number of messages received.
    """
    DOC_URI = 'did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/'
    PROTOCOL = 'basicmessage'
    VERSION = '1.0'

    def __init__(self):
        super().__init__()
        self.count = 0

    @route
    async def message(self, _msg, conn):
        """ Respond to basic messages with a count of messages received. """
        self.count += 1
        await conn.send_async({
            "@type": self.type("message"),
            "~l10n": {"locale": "en"},
            "sent_time": utils.timestamp(),
            "content": "{} message(s) received.".format(self.count)
        })


def main():
    """Create connection and start web server."""
    args = config()
    conn = StaticConnection(
        (args.my_verkey, args.my_sigkey),
        their_vk=args.their_verkey,
        endpoint=args.endpoint,
    )

    bmc = BasicMessageCounter()
    conn.route_module(bmc)

    async def handle(request):
        """ aiohttp handle POST. """
        await conn.handle(await request.read())
        raise web.HTTPAccepted()

    app = web.Application()
    app.add_routes([web.post('/', handle)])

    web.run_app(app, port=args.port)


if __name__ == '__main__':
    main()
