""" Static Agent Connection """
import asyncio
from typing import Union

import aiohttp

from .dispatcher import Dispatcher, Handler
from .message import Message
from .mtc import (
    MessageTrustContext,
    DESERIALIZE_OK,
    CONFIDENTIALITY,
    INTEGRITY,
    AUTHENTICATED_ORIGIN,
    NONREPUDIATION
)
from .type import Type
from . import crypto


class StaticConnection:
    """ A Static Agent Connection to another agent. """
    def __init__(
            self,
            endpoint: str,
            their_vk: Union[bytes, str],
            my_vk: Union[bytes, str],
            my_sk: Union[bytes, str],
            **kwargs
                ):
        """ Constructor

            params:
                endpoint - the http endpoint of the other agent
                their_vk - the verification key of the other agent
                my_vk - the verification key of the static agent
                my_sk - the signing key of the static agent
        """
        self.endpoint = endpoint
        self.their_vk = their_vk \
            if isinstance(their_vk, bytes) else crypto.b58_to_bytes(their_vk)
        self.my_vk = my_vk \
            if isinstance(my_vk, bytes) else crypto.b58_to_bytes(my_vk)
        self.my_sk = my_sk \
            if isinstance(my_sk, bytes) else crypto.b58_to_bytes(my_sk)

        self._dispatcher = kwargs.get('dispatcher', Dispatcher())

    def route(self, msg_type: str):
        """ Register route decorator. """
        def register_route_dec(func):
            self._dispatcher.add_handler(
                Handler(Type.from_str(msg_type), func)
            )
            return func

        return register_route_dec

    def route_module(self, module):
        """ Register a module for routing. """
        handlers = [
            Handler(msg_type, func)
            for msg_type, func in module.routes.items()
        ]
        return self._dispatcher.add_handlers(handlers)

    def clear_routes(self):
        """ Clear registered routes. """
        return self._dispatcher.clear_handlers()

    async def handle(self, packed_message):
        """ Unpack and handle message. """
        (msg, sender_vk, recip_vk) = crypto.unpack_message(
            packed_message,
            self.my_vk,
            self.my_sk
        )
        msg = Message.deserialize(msg)
        msg.mtc = MessageTrustContext(
            CONFIDENTIALITY | INTEGRITY | DESERIALIZE_OK,
            NONREPUDIATION
        )
        if sender_vk:
            msg.mtc[AUTHENTICATED_ORIGIN] = True

        msg.mtc.ad['sender_vk'] = sender_vk
        msg.mtc.ad['recip_vk'] = recip_vk
        await self._dispatcher.dispatch(msg, self)

    async def send_async(self, msg):
        """ Send a message to the agent connected through this
            StaticConnection.  This method should support both http and
            WS, eventually. Also Return Route.
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
            async with session.post(
                    self.endpoint,
                    data=packed_msg,
                    headers=headers
                        ) as resp:
                if resp.status != 202:
                    await self.handle(await resp.read())

    def send(self, msg):
        """ Send a message, blocking. """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.send_async(msg))

