""" Static Agent Connection """
import asyncio
from contextlib import contextmanager
from typing import Union, Callable

import aiohttp

from .dispatcher import Dispatcher, Handler
from .message import Message
from .module import Module
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
from .utils import AsyncClaimResource


class MessageUndeliverable(Exception):
    """When a message cannot be delivered."""


class StaticConnection:
    """ A Static Agent Connection to another agent. """
    def __init__(
            self,
            my_vk: Union[bytes, str],
            my_sk: Union[bytes, str],
            their_vk: Union[bytes, str],
            endpoint: str = None,
            dispatcher: Dispatcher = None
                ):
        """ Constructor

            params:
                endpoint - the http endpoint of the other agent
                their_vk - the verification key of the other agent
                my_vk - the verification key of the static agent
                my_sk - the signing key of the static agent
        """
        if not isinstance(my_vk, bytes) and not isinstance(my_vk, str):
            raise TypeError('`my_vk` must be bytes or str')
        if not isinstance(my_sk, bytes) and not isinstance(my_sk, str):
            raise TypeError('`my_sk` must be bytes or str')
        if not isinstance(their_vk, bytes) and not isinstance(their_vk, str):
            raise TypeError('`their_vk` must be bytes or str')

        self.endpoint = endpoint
        self.their_vk = their_vk \
            if isinstance(their_vk, bytes) else crypto.b58_to_bytes(their_vk)
        self.my_vk = my_vk \
            if isinstance(my_vk, bytes) else crypto.b58_to_bytes(my_vk)
        self.my_sk = my_sk \
            if isinstance(my_sk, bytes) else crypto.b58_to_bytes(my_sk)

        self._dispatcher = dispatcher if dispatcher else Dispatcher()
        self._pending_message = AsyncClaimResource()
        self._reply = None

    def route(self, msg_type: str):
        """ Register route decorator. """
        def register_route_dec(func):
            self._dispatcher.add_handler(
                Handler(Type.from_str(msg_type), func)
            )
            return func

        return register_route_dec

    def route_module(self, module: Module):
        """ Register a module for routing. """
        handlers = [
            Handler(msg_type, func)
            for msg_type, func in module.routes.items()
        ]
        return self._dispatcher.add_handlers(handlers)

    def clear_routes(self):
        """ Clear registered routes. """
        return self._dispatcher.clear_handlers()

    def unpack(self, packed_message: bytes) -> Message:
        """ Unpack a message, filling out metadata in the MTC """
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
        else:
            msg.mtc[AUTHENTICATED_ORIGIN] = False

        msg.mtc.ad['sender_vk'] = sender_vk
        msg.mtc.ad['recip_vk'] = recip_vk
        return msg

    def pack(self, msg: Union[dict, Message], anoncrypt=False):
        """ Pack a message for sending over the wire. """
        if not isinstance(msg, Message):
            if isinstance(msg, dict):
                msg = Message(msg)
            else:
                raise TypeError('msg must be type Message or dict')

        if anoncrypt:
            packed_message = crypto.pack_message(
                msg.serialize(),
                [self.their_vk],
            )
        else:
            packed_message = crypto.pack_message(
                msg.serialize(),
                [self.their_vk],
                self.my_vk,
                self.my_sk
            )

        return packed_message

    async def handle(self, packed_message: bytes):
        """ Unpack and dispatch message to handler. """
        msg = self.unpack(packed_message)
        if ('~transport' not in msg or
                'return_route' not in msg['~transport'] or
                msg['~transport']['return_route'] == 'none'):
            self._reply = None

        if self._pending_message.claimed():
            self._pending_message.satisfy(msg)
            return

        await self._dispatcher.dispatch(msg, self)

    async def send_async(
            self,
            msg: Union[dict, Message],
            *,
            return_route: str = None,
            plaintext: bool = False,
            anoncrypt: bool = False):
        """
        Send a message to the agent connected through this StaticConnection.
        """
        if plaintext and anoncrypt:
            raise RuntimeError(
                'plaintext and anoncrypt flags are mutually exclusive.'
            )

        if ((not return_route or return_route == 'none') and
                not self._reply and
                not self.endpoint):
            raise MessageUndeliverable(
                'Cannot send message;'
                ' no endpoint and no return route specified.'
            )

        if return_route and not self._reply:
            if '~transport' not in msg:
                msg['~transport'] = {}
            msg['~transport']['return_route'] = return_route

        # TODO Support WS
        if not plaintext:
            packed_message = self.pack(msg, anoncrypt=anoncrypt)
        else:
            packed_message = msg

        if self._reply:
            self._reply(packed_message)
            return

        async with aiohttp.ClientSession() as session:
            headers = {'content-type': 'application/ssi-agent-wire'}
            async with session.post(
                    self.endpoint,
                    data=packed_message,
                    headers=headers) as resp:

                body = await resp.read()
                if resp.status != 200 or resp.status != 202:
                    raise MessageUndeliverable(
                        'Error while sending message: {} {}'.format(
                            resp.status,
                            body
                        )
                    )
                if resp.status == 200 and body:
                    if return_route is None or return_route == 'none':
                        raise RuntimeError(
                            'Response received when no response was '
                            'expected'
                        )

                    await self.handle(body)

                if (not body and
                        return_route and
                        return_route != 'none' and
                        self._pending_message.claimed()):
                    self._pending_message.satisfy(None)

    async def send_and_await_reply_async(
            self,
            msg: Union[dict, Message],
            *,
            return_route: str = "all",
            plaintext: bool = False,
            anoncrypt: bool = False,
            timeout: int = 0):
        """Send a message and wait for a reply."""

        self._pending_message.claim()
        await self.send_async(
            msg,
            return_route=return_route,
            plaintext=plaintext,
            anoncrypt=anoncrypt,
        )
        reply = await self.await_message(timeout)
        return reply

    @contextmanager
    def reply_handler(
            self,
            send: Callable[[str], None]):
        """
        Set a reply handler to be used in sending messages rather than opening
        a new connection.
        """
        self._reply = send
        yield
        self._reply = None

    def send(self, *args, **kwargs):
        """ Send a message, blocking. """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.send_async(*args, **kwargs))

    def send_and_await_reply(self, *args, **kwargs):
        """ Send a message and await reply, blocking. """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.send_and_await_reply_async(*args, **kwargs)
        )

    async def await_message(self, timeout: int = 0):
        """
        Bypass dispatching to a handler and return the next handled message
        here.
        """
        if not self._pending_message.claimed():
            self._pending_message.claim()

        if timeout > 0:
            return await asyncio.wait_for(
                self._pending_message.retrieve(),
                timeout
            )

        return await self._pending_message.retrieve()
