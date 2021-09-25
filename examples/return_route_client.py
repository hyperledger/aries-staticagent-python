"""Example client to return route capable agent.

This example is intended to be run with return_route_server to demonstrate
return routing.
"""

import hashlib
import os
from aries_staticagent import StaticConnection, Target, crypto, utils


def main():
    """Send a message and await the reply."""
    their_vk, _ = crypto.create_keypair(seed=hashlib.sha256(b"server").digest())
    conn = StaticConnection.from_seed(
        hashlib.sha256(b"client").digest(),
        Target(
            their_vk=their_vk,
            endpoint="http://localhost:{}".format(os.environ.get("PORT", 3000)),
        ),
    )
    reply = conn.send_and_await_returned(
        {
            "@type": "https://didcomm.org/basicmessage/1.0/message",
            "~l10n": {"locale": "en"},
            "sent_time": utils.timestamp(),
            "content": "The Cron script has been executed.",
        },
        return_route="all",
    )
    print("Msg from conn:", reply and reply.pretty_print())


if __name__ == "__main__":
    main()
