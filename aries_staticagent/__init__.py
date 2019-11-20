""" Aries Static Agent Library.
"""

from .static_connection import StaticConnection, MessageDeliveryError
from .module import Module, route
from .message import Message

from . import crypto


def keygen():
    """ Convenience method for generating and printing a keypair and DID.
        DID is generated from the first 16 bytes of the VerKey.
    """
    vk_bytes, sk_bytes = crypto.create_keypair()

    # TODO implement DID creation as described in the Peer DID Spec
    # Link: https://openssi.github.io/peer-did-method-spec/index.html
    did_bytes = vk_bytes[0:16]

    my_vk = crypto.bytes_to_b58(vk_bytes)
    my_sk = crypto.bytes_to_b58(sk_bytes)
    did = crypto.bytes_to_b58(did_bytes)

    print('Static Agent Connection info for full agent:\n\tDID: {}\n\tVK: {}\n'
          .format(did, my_vk))
    print('Static Agent Connection info for static agent:\n\tVK: {}\n\tSK: {}'
          .format(my_vk, my_sk))
