"""Cron script example.

This file is intended to be run as a cron script. Upon execution, it does
it's thing and shuts down.
"""

from aries_staticagent import StaticConnection, utils

from common import config

def main():
    """Send message from cron job."""
    args = config()
    conn = StaticConnection.from_parts(
        (args.my_verkey, args.my_sigkey),
        their_vk=args.their_verkey,
        endpoint=args.endpoint,
    )
    conn.send({
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/"
                 "basicmessage/1.0/message",
        "~l10n": {"locale": "en"},
        "sent_time": utils.timestamp(),
        "content": "The Cron script was executed."
    })


if __name__ == '__main__':
    main()
