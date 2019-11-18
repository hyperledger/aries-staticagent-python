""" Webserver with module example. """
import argparse
import os
from aiohttp import web

from aries_staticagent import StaticConnection, Module, route, utils


def environ_or_required(key):
    """ Pull arg from environment or require it in args. """
    if os.environ.get(key):
        return {'default': os.environ.get(key)}

    return {'required': True}


def config():
    """ Get StaticConnection parameters from env or command line args. """
    parser = argparse.ArgumentParser()
    # endpoint can be http or ws, auto handled by staticagent library.
    parser.add_argument(
        '--endpoint',
        **environ_or_required('ARIES_ENDPOINT')
    )
    parser.add_argument(
        '--endpointkey',
        **environ_or_required('ARIES_ENDPOINT_KEY')
    )
    parser.add_argument(
        '--mypublickey',
        **environ_or_required('ARIES_MY_PUBLIC_KEY')
    )
    parser.add_argument(
        '--myprivatekey',
        **environ_or_required('ARIES_MY_PRIVATE_KEY')
    )
    parser.add_argument(
        '--port',
        **environ_or_required('PORT')
    )
    args = parser.parse_args()
    return args


class BasicMessageCounter(Module):
    """ A BasicMessage module that responds with the number of messages
        received.
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
    """ Create connection and start web server. """
    args = config()
    conn = StaticConnection(
        (args.mypublickey, args.myprivatekey),
        their_vk=args.endpointkey,
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
