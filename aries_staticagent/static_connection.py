"""Static Agent Connection."""
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


class MessageUndeliverable(Exception):
    """When a message cannot be delivered."""


class ConditionallyAwaitFutureMessage:
    """Async construct for waiting for a message that meets a condition."""

    def __init__(self, condition: Callable[[Message], bool] = None):
        self._condition = condition
        self._future = asyncio.Future()
        self._pending_task: asyncio.Task = None

    def condition_met(self, msg: Message) -> bool:
        """Test whether the condition has been met for this message."""
        if not self._condition:
            return True
        return self._condition(msg)

    def wait(self) -> asyncio.Task:
        """Wait for a message meeting the given condition."""
        if not self._pending_task:
            self._pending_task = asyncio.ensure_future(self._future)
        return self._pending_task

    def set_message(self, msg: Message):
        """Set the message, fulfilling the future."""
        self._future.set_result(msg)


class StaticConnection:
    """A Static Agent Connection to another agent."""

    def __init__(
            self,
            my_vk: Union[bytes, str],
            my_sk: Union[bytes, str],
            their_vk: Union[bytes, str] = None,
            endpoint: str = None,
            dispatcher: Dispatcher = None
                ):
        """
        Construct new static connection.

        params:
            my_vk - the verification key of the static agent
            my_sk - the signing key of the static agent
            their_vk - the verification key of the other agent
            endpoint - the http endpoint of the other agent
        """
        if endpoint and not isinstance(endpoint, str):
            raise TypeError('`endpoint` must be a str')

        self.endpoint = endpoint

        if not their_vk:
            self.their_vk = None
        elif isinstance(their_vk, bytes):
            self.their_vk = their_vk
            self.their_vk_b58 = crypto.bytes_to_b58(their_vk)
        elif isinstance(their_vk, str):
            self.their_vk = crypto.b58_to_bytes(their_vk)
            self.their_vk_b58 = their_vk
        else:
            raise TypeError('`their_vk` must be bytes or str')

        if isinstance(my_vk, bytes):
            self.my_vk = my_vk
            self.my_vk_b58 = crypto.bytes_to_b58(my_vk)
        elif isinstance(my_vk, str):
            self.my_vk_b58 = my_vk
            self.my_vk = crypto.b58_to_bytes(my_vk)
        else:
            raise TypeError('`my_vk` must be bytes or str')

        self.did = crypto.bytes_to_b58(self.my_vk[:16])

        if isinstance(my_sk, bytes):
            self.my_sk = my_sk
            self.my_sk_b58 = crypto.bytes_to_b58(my_sk)
        elif isinstance(my_sk, str):
            self.my_sk_b58 = my_sk
            self.my_sk = crypto.b58_to_bytes(my_sk)
        else:
            raise TypeError('`my_sk` must be bytes or str')

        self._dispatcher = dispatcher if dispatcher else Dispatcher()
        self._future_message: ConditionallyAwaitFutureMessage = None
        self._reply: Callable[[bytes], None] = None

    @contextmanager
    def future_message(
            self,
            condition: Callable[[Message], bool] = None) -> asyncio.Task:
        """Get a handle to a future message matching condition."""
        if not self._future_message:
            self._future_message = \
                ConditionallyAwaitFutureMessage(condition)

        yield self._future_message.wait()

        self._future_message = None

    @contextmanager
    def reply_handler(
            self,
            send: Callable[[bytes], None]):
        """
        Set a reply handler to be used in sending messages rather than opening
        a new connection.
        """
        self._reply = send
        yield
        self._reply = None

    def route(self, msg_type: str) -> Callable:
        """Register route decorator."""
        def register_route_dec(func):
            self._dispatcher.add_handler(
                Handler(Type.from_str(msg_type), func)
            )
            return func

        return register_route_dec

    def route_module(self, module: Module):
        """Register a module for routing."""
        handlers = [
            Handler(msg_type, func)
            for msg_type, func in module.routes.items()
        ]
        return self._dispatcher.add_handlers(handlers)

    def clear_routes(self):
        """Clear registered routes."""
        return self._dispatcher.clear_handlers()

    def unpack(self, packed_message: bytes) -> Message:
        """Unpack a message, filling out metadata in the MTC."""
        try:
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
        except ValueError:
            msg = Message.deserialize(packed_message)
            msg.mtc = MessageTrustContext(
                DESERIALIZE_OK,
                CONFIDENTIALITY | INTEGRITY | AUTHENTICATED_ORIGIN
            )

        return msg

    def pack(self, msg: Union[dict, Message], anoncrypt=False) -> bytes:
        """Pack a message for sending over the wire."""
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
        """Unpack and dispatch message to handler."""
        msg = self.unpack(packed_message)
        if ('~transport' not in msg or
                'return_route' not in msg['~transport'] or
                msg['~transport']['return_route'] == 'none'):
            self._reply = None

        if self._future_message and self._future_message.condition_met(msg):
            # Skip normal dispatch if a future message is being awaited and the
            # condition is met.
            self._future_message.set_message(msg)
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
            raise ValueError(
                'plaintext and anoncrypt flags are mutually exclusive.'
            )

        if ((not return_route or return_route == 'none') and
                not self._reply and
                not self.endpoint):
            raise MessageUndeliverable(
                'Cannot send message;'
                ' no endpoint and no return route.'
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
                if resp.status != 200 and resp.status != 202:
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

    async def await_message(
            self,
            condition: Callable[[Message], bool] = None,
            timeout: int = 0) -> Message:
        """
        Bypass dispatching to a handler and return the next handled message
        matching the given condition here.
        """
        with self.future_message(condition) as future_msg:
            if timeout > 0:
                msg = await asyncio.wait_for(
                    future_msg,
                    timeout
                )
            else:
                msg = await future_msg
            return msg

    async def send_and_await_reply_async(
            self,
            msg: Union[dict, Message],
            *,
            condition: Callable[[Message], bool] = None,
            return_route: str = "all",
            plaintext: bool = False,
            anoncrypt: bool = False,
            timeout: int = 0) -> Message:
        """Send a message and wait for a reply."""

        with self.future_message():
            await self.send_async(
                msg,
                return_route=return_route,
                plaintext=plaintext,
                anoncrypt=anoncrypt,
            )
            reply = await self.await_message(condition, timeout)
            return reply

    def send(self, *args, **kwargs):
        """Blocking wrapper around send_async."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.send_async(*args, **kwargs))

    def send_and_await_reply(self, *args, **kwargs) -> Message:
        """Blocking wrapper around send_and_await_reply_async."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.send_and_await_reply_async(*args, **kwargs)
        )
