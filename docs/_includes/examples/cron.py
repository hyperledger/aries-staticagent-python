""" Cron script example. """
# This file is intended to be run as a cron script. Upon execution, it does
# it's thing and shuts down.

import argparse
import os

from aries_staticagent import StaticConnection, utils


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
    args = parser.parse_args()
    return args


def main():
    """ Cron example. """
    args = config()
    conn = StaticConnection(
        (args.mypublickey, args.myprivatekey),
        their_vk=args.endpointkey,
        endpoint=args.endpoint,
    )
    conn.send({
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/"
                 "basicmessage/1.0/message",
        "~l10n": {"locale": "en"},
        "sent_time": utils.timestamp(),
        "content": "The Cron Script has been executed."
    })


if __name__ == '__main__':
    main()
