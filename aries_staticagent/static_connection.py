"""Static Agent Connection."""
import asyncio
import json
from contextlib import contextmanager
from typing import (
    Union, Callable, Awaitable, Dict,
    Tuple, Sequence, Optional, List
)
from collections import namedtuple

from . import crypto
from .dispatcher import Dispatcher, Handler
from .message import Message
from .module import Module
from .mtc import MessageTrustContext
from .type import Type
from .utils import ensure_key_bytes, forward_msg, http_send


Send = Callable[[bytes, str], Awaitable[bytes]]
Reply = Callable[[bytes], Awaitable[None]]
ConditionFutureMap = Dict[Callable[[Message], bool], asyncio.Future]


class MessageDeliveryError(Exception):
    """When a message cannot be delivered."""
    def __init__(self, *, status: int = None, msg: str = None):
        super().__init__(msg)
        self.status = status


class StaticConnection:
    """A Static Agent Connection to another agent."""

    Keys = namedtuple('KeyPair', 'verkey, sigkey')

    def __init__(
            self,
            keys: Tuple[Union[bytes, str], Union[bytes, str]],
            *,
            endpoint: str = None,
            their_vk: Union[bytes, str] = None,
            recipients: Sequence[Union[bytes, str]] = None,
            routing_keys: Sequence[Union[bytes, str]] = None,
            send: Send = None,
            dispatcher: Dispatcher = None):

        if their_vk and recipients:
            raise ValueError('their_vk and recipients are mutually exclusive.')

        self.keys = StaticConnection.Keys(*map(ensure_key_bytes, keys))
        self.endpoint: Optional[str] = endpoint
        self.recipients: List[bytes] = None
        self.routing_keys: List[bytes] = None

        if their_vk:
            self.recipients = [ensure_key_bytes(their_vk)]

        if recipients:
            self.recipients = list(map(ensure_key_bytes, recipients))

        if routing_keys:
            self.routing_keys = list(map(ensure_key_bytes, routing_keys))

        self._dispatcher = dispatcher if dispatcher else Dispatcher()
        self._next: ConditionFutureMap = {}
        self._reply: Reply = None
        self._send: Send = send if send else http_send

    def update(
            self,
            *,
            endpoint: str = None,
            their_vk: Union[bytes, str] = None,
            recipients: Sequence[Union[bytes, str]] = None,
            routing_keys: Sequence[Union[bytes, str]] = None,
            **_kwargs):
        """Update their information."""
        if their_vk and recipients:
            raise ValueError('their_vk and recipients are mutually exclusive.')

        if endpoint:
            self.endpoint = endpoint

        if their_vk:
            self.recipients = [ensure_key_bytes(their_vk)]

        if recipients:
            self.recipients = list(map(ensure_key_bytes, recipients))

        if routing_keys:
            self.routing_keys = list(map(ensure_key_bytes, routing_keys))

    @property
    def verkey(self):
        """My verification key for this connection."""
        return self.keys.verkey

    @property
    def verkey_b58(self):
        """Get Base58 encoded my_vk."""
        return crypto.bytes_to_b58(self.keys.verkey)

    @property
    def sigkey(self):
        """My signing key for this connection."""
        return self.keys.sigkey

    @property
    def did(self):
        """Get verkey based DID for this connection."""
        return crypto.bytes_to_b58(self.keys.verkey[:16])

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

    async def dispatch(self, message):
        """
        Dispatch message to handler.
        """
        await self._dispatcher.dispatch(message, self)

    @contextmanager
    def next(
            self,
            type_: str = None,
            condition: Callable[[Message], bool] = None):
        """
        Context manager to claim the next message matching condtion, allowing
        temporary bypass of regular dispatch.

        This will consume only the next message matching condition. If you need
        to consume more than one or two, consider using a standard message
        handler or overriding the default dispatching mechanism.
        """
        if condition and type_:
            raise ValueError('Expected type or condtion, not both.')
        if condition and not callable(condition):
            raise TypeError('condition must be Callable[[Message], bool]')

        if not condition and not type_:
            # Collect everything
            def _default(_msg):
                return True
            selected_condition = _default

        if type_:
            def _matches_type(msg):
                return msg.type == type_
            selected_condition = _matches_type

        if condition:
            selected_condition = condition

        next_message: asyncio.Future[Message] = asyncio.Future()
        self._next[selected_condition] = next_message

        yield next_message

        del self._next[selected_condition]

    def unpack(self, packed_message: Union[bytes, dict]) -> Message:
        """Unpack a message, filling out metadata in the MTC."""
        try:
            (unpacked_msg, sender_vk, recip_vk) = crypto.unpack_message(
                packed_message,
                self.verkey,
                self.sigkey
            )
            msg = Message.deserialize(unpacked_msg)
            msg.mtc = MessageTrustContext()
            if sender_vk:
                msg.mtc.set_authcrypted(sender_vk, recip_vk)
            else:
                msg.mtc.set_anoncrypted(recip_vk)

        except (ValueError, KeyError):
            if not isinstance(packed_message, bytes):
                raise TypeError(
                    'Expected bytes, got {}'.format(type(msg).__name__)
                )
            msg = Message.deserialize(packed_message)
            msg.mtc = MessageTrustContext()
            msg.mtc.set_plaintext()

        return msg

    def pack(
            self,
            msg: Union[dict, Message],
            anoncrypt=False,
            plaintext=False) -> bytes:
        """Pack a message for sending over the wire."""
        if plaintext and anoncrypt:
            raise ValueError(
                'plaintext and anoncrypt flags are mutually exclusive.'
            )

        if not isinstance(msg, Message):
            if isinstance(msg, dict):
                msg = Message(msg)
            else:
                raise TypeError('msg must be type Message or dict')

        if plaintext:
            return json.dumps(msg).encode('ascii')

        if not self.recipients:
            raise RuntimeError('No recipients for whom to pack this message')

        if anoncrypt:
            packed_message = crypto.pack_message(
                msg.serialize(),
                self.recipients,
            )
        else:
            packed_message = crypto.pack_message(
                msg.serialize(),
                self.recipients,
                self.verkey,
                self.sigkey,
            )

        if self.routing_keys:
            to = self.recipients[0]
            for routing_key in self.routing_keys:
                packed_message = crypto.pack_message(
                    forward_msg(to=to, msg=packed_message).serialize(),
                    [routing_key],
                )
                to = routing_key

        return json.dumps(packed_message).encode('ascii')

    @contextmanager
    def reply_handler(
            self,
            reply: Reply):
        """
        Set a reply handler to be used in sending messages rather than opening
        a new connection.
        """
        self._reply = reply
        yield
        self._reply = None

    def can_reply(self) -> bool:
        """Check whether connection can reply."""
        return self._reply is not None

    async def reply(self, message: bytes):
        """Call reply method."""
        if self._reply is None:
            raise RuntimeError('Cannot reply; no reply handler is set')
        await self._reply(message)

    async def handle(self, packed_message: bytes):
        """Unpack and dispatch message to handler."""
        msg = self.unpack(packed_message)
        if ('~transport' not in msg or
                'return_route' not in msg['~transport'] or
                msg['~transport']['return_route'] == 'none'):
            self._reply = None

        for condition, next_message_future in self._next.items():
            if condition(msg) and not next_message_future.done():
                next_message_future.set_result(msg)
                return

        await self.dispatch(msg)

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
        # not can_reply indicates this is an outbound message
        if return_route and not self.can_reply():
            if '~transport' not in msg:
                msg['~transport'] = {}
            msg['~transport']['return_route'] = return_route

        packed_message = self.pack(
            msg, anoncrypt=anoncrypt, plaintext=plaintext
        )

        if self.can_reply():
            await self.reply(packed_message)
            return

        if not self.endpoint:
            raise MessageDeliveryError(
                msg='Cannot send message; no endpoint and no return route.'
            )

        try:
            response = await self._send(
                packed_message,
                self.endpoint
            )
        except Exception as err:
            raise MessageDeliveryError(msg=str(err)) from err

        if response:
            if return_route is None or return_route == 'none':
                raise RuntimeError(
                    'Response received when no response was expected'
                )
            await self.handle(response)

    async def send_and_await_reply_async(
            self,
            msg: Union[dict, Message],
            *,
            type_: str = None,
            condition: Callable[[Message], bool] = None,
            return_route: str = "all",
            plaintext: bool = False,
            anoncrypt: bool = False,
            timeout: int = None) -> Message:
        """Send a message and wait for a reply."""

        with self.next(type_=type_, condition=condition) as next_message:
            await self.send_async(
                msg,
                return_route=return_route,
                plaintext=plaintext,
                anoncrypt=anoncrypt,
            )
            return await asyncio.wait_for(next_message, timeout)

    async def await_message(
            self,
            *,
            type_: str = None,
            condition: Callable[[Message], bool] = None,
            timeout: int = None):
        """
        Wait for a message.

        Note that it's possible for a message to arrive just before or during
        the setup of this function. If it's likely that a message will arrive
        as a result of an action taken prior to calling await_message, use the
        `next` context manager instead.
        """
        with self.next(type_, condition=condition) as next_message:
            return await asyncio.wait_for(next_message, timeout)

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
