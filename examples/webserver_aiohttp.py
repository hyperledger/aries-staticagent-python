# This file is intended to be run as a cron script. Upon execution, it does it's thing and shuts down.
import argparse
import os

from aries_staticagent import AriesAgentConnection, ariesutils

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
parser.add_argument('--myprivatekey', **environ_or_required('ARIES_MY_PRIVATE_KEY'))
args = parser.parse_args()

# Config End

a = AriesAgentConnection(args.endpoint, args.endpointkey, args.myprivatekey)

a.returnroute = "thread"

@a.handle("did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message")
def basic_message(msg):
    a.send({
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message",
        "~l10n": {"locale": "en"},
        "sent_time": ariesutils.timestamp_now(),
        "content": "You Said: {}".format(msg.content)
    })


async def handle(request):
    a.process_inbound_message(request.body)

app = web.Application()
app.add_routes([web.get('/', handle)])

web.run_app(app)
