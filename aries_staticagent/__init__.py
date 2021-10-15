""" Aries Static Agent Library.
"""

from .connection import Connection, Keys, Target, MessageDeliveryError
from .module import Module, ModuleRouter
from .message import (
    Message,
    MsgType,
    MsgVersion,
    ProtocolIdentifier,
    InvalidProtocolIdentifier,
    InvalidType,
)
from .dispatcher import Dispatcher, HandlerDispatcher, QueueDispatcher
from .dispatcher.queue_dispatcher import MsgQueue
from . import operators

from . import crypto

__all__ = [
    "Connection",
    "Dispatcher",
    "HandlerDispatcher",
    "InvalidProtocolIdentifier",
    "InvalidType",
    "Keys",
    "Message",
    "MessageDeliveryError",
    "Module",
    "ModuleRouter",
    "MsgQueue",
    "MsgType",
    "MsgVersion",
    "ProtocolIdentifier",
    "QueueDispatcher",
    "Target",
    "keygen",
    "operators",
]


def keygen():
    """Convenience method for generating and printing a keypair and DID.
    DID is generated from the first 16 bytes of the VerKey.
    """
    vk_bytes, sk_bytes = crypto.create_keypair()

    # TODO implement DID creation as described in the Peer DID Spec
    # Link: https://openssi.github.io/peer-did-method-spec/index.html
    did_bytes = vk_bytes[0:16]

    my_vk = crypto.bytes_to_b58(vk_bytes)
    my_sk = crypto.bytes_to_b58(sk_bytes)
    did = crypto.bytes_to_b58(did_bytes)

    print(
        f"Static Agent Connection info for full agent:\n\tDID: {did}\n\tVK: {my_vk}\n"
    )
    print(
        f"Static Agent Connection info for static agent:\n\tVK: {my_vk}\n\tSK: {my_sk}"
    )
