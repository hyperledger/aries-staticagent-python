"""Example client to return route capable agent.

This example is intended to be run with return_route_server to demonstrate
return routing.
"""

import hashlib
from aries_staticagent import StaticConnection, crypto, utils


def main():
    """Send a message and await the reply."""
    keys = crypto.create_keypair(
        seed=hashlib.sha256(b'client').digest()
    )
    their_vk, _ = crypto.create_keypair(
        seed=hashlib.sha256(b'server').digest()
    )
    conn = StaticConnection(
        keys, their_vk=their_vk, endpoint='http://localhost:3000'
    )

    reply = conn.send_and_await_reply({
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/"
                 "basicmessage/1.0/message",
        "~l10n": {"locale": "en"},
        "sent_time": utils.timestamp(),
        "content": "The Cron Script has been executed."
    }, return_route='all')
    print('Msg from conn:', reply and reply.pretty_print())


if __name__ == '__main__':
    main()
