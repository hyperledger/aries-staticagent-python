""" Aries Static Agent Library.
"""
import asyncio
from typing import Union

import aiohttp

from .dispatcher import Dispatcher
from .message import Message
from .mtc import (
    MessageTrustContext,
    DESERIALIZE_OK,
    CONFIDENTIALITY,
    INTEGRITY,
    AUTHENTICATED_ORIGIN,
    NONREPUDIATION
)
from . import crypto

class StaticAgentConnection:
    """ A Static Agent Connection to another agent. """
    def __init__(
            self,
            endpoint: str,
            their_vk: Union[bytes, str],
            my_vk: Union[bytes, str],
            my_sk: Union[bytes, str],
            dispatcher: Dispatcher = None
                ):
        """ Constructor

            params:
                endpoint - the http endpoint of the other agent
                their_vk - the verification key of the other agent
                my_vk - the verification key of the static agent
                my_sk - the signing key of the static agent
        """
        self.endpoint = endpoint
        self.their_vk = their_vk if isinstance(their_vk, bytes) else crypto.b58_to_bytes(their_vk)
        self.my_vk = my_vk if isinstance(my_vk, bytes) else crypto.b58_to_bytes(my_vk)
        self.my_sk = my_sk if isinstance(my_sk, bytes) else crypto.b58_to_bytes(my_sk)

        self._dispatcher = dispatcher if not None else Dispatcher()

    def route(self, msg_type):
        """ Wraps dispatcher.route """
        return self._dispatcher.route(msg_type)

    def route_module(self, module):
        """ Register a module for routing. Wraps dispatcher.route_module """
        return self._dispatcher.route_module(module)

    def clear_routes(self):
        """ Clear registered routes. Wraps dispatcher.clear_routes """
        return self._dispatcher.clear_routes()

    def clear_modules(self):
        """ Clear registered modules. Wraps dispatcher.clear_modules"""
        return self._dispatcher.clear_modules()

    async def handle(self, packed_message):
        """ Unpack and handle message. """
        (msg, sender_vk, recip_vk) = crypto.unpack_message(packed_message, self.my_vk, self.my_sk)
        msg = Message.deserialize(msg)
        msg.mtc = MessageTrustContext(
            CONFIDENTIALITY | INTEGRITY | DESERIALIZE_OK,
            NONREPUDIATION
        )
        msg.mtc.ad['sender_vk'] = sender_vk
        msg.mtc.ad['recip_vk'] = recip_vk
        await self._dispatcher.dispatch(msg, self)

    async def send_async(self, msg):
        """ Send a message to the agent connected through this StaticAgentConnection.
            This method should support both http and WS, eventually. Also Return Route.
        """
        #TODO Support WS
        if isinstance(msg, dict):
            msg = Message(msg)

        packed_msg = crypto.pack_message(
            msg.serialize(),
            [self.their_vk],
            self.my_vk,
            self.my_sk
        )

        async with aiohttp.ClientSession() as session:
            headers = {'content-type': 'application/ssi-agent-wire'}
            async with session.post(self.endpoint, data=packed_msg, headers=headers) as resp:
                if resp.status != 202:
                    await self.handle(await resp.read())

    def send(self, msg):
        """ Send a message, blocking. """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.send_async(msg))


def keygen():
    """ Convenience method for generating and printing a keypair and DID.
        DID is generated from the first 16 bytes of the VerKey.
    """
    vk_bytes, sk_bytes = crypto.create_keypair()

    # TODO implement DID creation as described in the Peer DID Spec
    # Link: https://openssi.github.io/peer-did-method-spec/index.html
    did_bytes = vk_bytes[0:16]

    vk = crypto.bytes_to_b58(vk_bytes)
    sk = crypto.bytes_to_b58(sk_bytes)
    did = crypto.bytes_to_b58(did_bytes)

    print('For full agent:\n\tDID: {}\n\tVK: {}\n'.format(did, vk))
    print('For static agent:\n\tVK: {}\n\tSK: {}'.format(vk, sk))
