"""Webserver example."""
import argparse
import os
from aiohttp import web

from aries_staticagent import StaticConnection, utils


def environ_or_required(key):
    """Pull arg from environment or require it in args."""
    if os.environ.get(key):
        return {'default': os.environ.get(key)}

    return {'required': True}

def config():
    """Get StaticConnection parameters from env or command line args."""
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


def main():
    """Create StaticConnection and start web server."""
    args = config()
    conn = StaticConnection(
        (args.mypublickey, args.myprivatekey),
        their_vk=args.endpointkey,
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
        with conn.reply_handler(response.append):
            await conn.handle(await request.read())

        if response:
            return web.Response(text=response.pop())

        raise web.HTTPAccepted()

    app = web.Application()
    app.add_routes([web.post('/', handle)])

    web.run_app(app, port=args.port)


if __name__ == '__main__':
    main()
