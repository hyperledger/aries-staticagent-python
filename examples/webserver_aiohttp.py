# This file is intended to be run as a cron script. Upon execution, it does it's thing and shuts down.
import argparse
import os

from aries_staticagent import StaticAgentConnection, utils

from aiohttp import web

# Config Start

def environ_or_required(key):
    if os.environ.get(key):
        return {'default': os.environ.get(key)}
    else:
        return {'required': True}

# above from https://stackoverflow.com/questions/10551117/setting-options-from-environment-variables-when-using-argparse
# Thought: Should we include arg parsing help into the staticagent library?

# endpoint can be http or ws, auto handled by staticagent library.

parser = argparse.ArgumentParser()
parser.add_argument('--endpoint', **environ_or_required('ARIES_ENDPOINT'))
parser.add_argument('--endpointkey', **environ_or_required('ARIES_ENDPOINT_KEY'))
parser.add_argument('--mypublickey', **environ_or_required('ARIES_MY_PUBLIC_KEY'))
parser.add_argument('--myprivatekey', **environ_or_required('ARIES_MY_PRIVATE_KEY'))
parser.add_argument('--port', **environ_or_required('PORT'))
args = parser.parse_args()

# Config End

a = StaticAgentConnection(args.endpoint, args.endpointkey, args.mypublickey, args.myprivatekey)
#a.returnroute = "thread"

@a.route("did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message")
async def basic_message(agent, msg):
    await a.send({
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message",
        "~l10n": {"locale": "en"},
        "sent_time": utils.timestamp(),
        "content": "You said: {}".format(msg['content'])
    })


async def handle(request):
    await a.handle(await request.read())
    raise web.HTTPAccepted()

app = web.Application()
app.add_routes([web.post('/', handle)])

web.run_app(app, port=args.port)
