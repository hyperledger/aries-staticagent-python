"""Methods common to examples."""

import argparse
import os
from aries_staticagent import Keys, Target


def environ_or_required(key):
    """Pull arg from environment or require it in args."""
    if os.environ.get(key):
        return {'default': os.environ.get(key)}

    return {'required': True}


def config():
    """Get StaticConnection parameters from env or command line args."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--endpoint',
        **environ_or_required('ARIES_ENDPOINT')
    )
    parser.add_argument(
        '--their-verkey',
        **environ_or_required('ARIES_ENDPOINT_KEY')
    )
    parser.add_argument(
        '--my-verkey',
        **environ_or_required('ARIES_MY_PUBLIC_KEY')
    )
    parser.add_argument(
        '--my-sigkey',
        **environ_or_required('ARIES_MY_PRIVATE_KEY')
    )
    parser.add_argument(
        '--port',
        default=os.environ.get('PORT', 3000)
    )
    args = parser.parse_args()
    return (
        Keys(args.my_verkey, args.my_sigkey),
        Target(endpoint=args.endpoint, their_vk=args.their_verkey),
        args
    )
