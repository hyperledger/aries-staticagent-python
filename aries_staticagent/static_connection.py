"""Static Agent Connection."""
import asyncio
import json
from contextlib import contextmanager
from typing import (
    Union, Callable, Awaitable, Dict,
    Tuple, Sequence, Optional, List,
    Set
)
import uuid
from collections import namedtuple

from . import crypto
from .dispatcher import Dispatcher, Handler
from .message import Message
from .module import Module
from .mtc import MessageTrustContext
from .type import Type
from .utils import ensure_key_bytes, forward_msg, http_send


Send = Callable[[bytes, str], Awaitable[Optional[bytes]]]
SessionSend = Callable[[bytes], Awaitable[None]]
ConditionFutureMap = Dict[Callable[[Message], bool], asyncio.Future]


class MessageDeliveryError(Exception):
    """When a message cannot be delivered."""
    def __init__(self, *, status: int = None, msg: str = None):
        super().__init__(msg)
        self.status = status


class Session:
    """An active transport-layer connection/socket providing a send method."""

    THREAD_ALL = 'all'

    def __init__(self, send: SessionSend, thread: str = None):
        if send is None:
            raise TypeError('Must supply send method to Session')

        if not callable(send) and not asyncio.iscoroutine(send):
            raise TypeError(
                'Invalid send method; expected coroutine or function, got {}'
                .format(type(send).__name__)
            )

        self._id = str(uuid.uuid4())
        self._send = send
        self._thread = thread
        self._status = None

    @property
    def session_id(self):
        """Unique Identifier for this session."""
        return self._id

    @property
    def thread(self):
        """Get this session's assigned thread."""
        return self._thread

    def update_thread_from_msg(self, msg: Message):
        """Update a thread with info from the ~transport decorator."""
        if '~transport' not in msg and self._thread is None:
            return

        transport = msg['~transport']
        if transport['return_route'] == 'all':
            self._thread = self.THREAD_ALL
            return

        if transport['return_route'] == 'thread':
            self._thread = transport['return_route_thread']
            return

        if transport['return_route'] == 'none':
            self._thread = None
            return

    def returning(self) -> bool:
        """Session set to return route?"""
        return bool(self._thread)

    def thread_all(self) -> bool:
        """Session is set to return all messages."""
        return self.thread == self.THREAD_ALL

    async def send(self, message: bytes):
        """Send a packed message to this session."""
        if not self.returning():
            raise RuntimeError('Session is not set to return route')

        ret = self._send(message)
        if asyncio.iscoroutine(ret):
            return await ret

        return ret

    def __hash__(self):
        return hash(self.session_id)

    def __eq__(self, other):
        if not isinstance(other, Session):
            return False
        return self.session_id == other.session_id


class ConnectionInfo:
    """Info required to send a message to a connection."""

    Keypair = namedtuple('Keypair', 'verkey, sigkey')

    def __init__(
            self,
            keys: Tuple[Union[bytes, str], Union[bytes, str]],
            *,
            endpoint: str = None,
            their_vk: Union[bytes, str] = None,
            recipients: Sequence[Union[bytes, str]] = None,
            routing_keys: Sequence[Union[bytes, str]] = None
    ):

        if their_vk and recipients:
            raise ValueError('their_vk and recipients are mutually exclusive.')

        self.keys = self.Keypair(*map(ensure_key_bytes, keys))
        self.endpoint: Optional[str] = endpoint
        self.recipients: Optional[List[bytes]] = None
        self.routing_keys: Optional[List[bytes]] = None

        if their_vk:
            self.recipients = [ensure_key_bytes(their_vk)]

        if recipients:
            self.recipients = list(map(ensure_key_bytes, recipients))

        if routing_keys:
            self.routing_keys = list(map(ensure_key_bytes, routing_keys))

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


class StaticConnection(ConnectionInfo):
    """Create a Static Agent Connection to another agent.

    The following will create a Static Connection with just the receiving end
    in place. This makes it possible to receive a message over this connection
    without yet knowing where messages will be sent.

    >>> my_keys = crypto.create_keypair()
    >>> connection = StaticConnection(my_keys)

    To create a Static Agent Connection with both ends configured:
    >>> their_pretend_verkey = crypto.create_keypair()[0]
    >>> connection = StaticConnection(my_keys, their_vk=their_pretend_verkey)
    >>> connection.recipients == [their_pretend_verkey]
    True

    Or, when there are multiple recipients:
    >>> pretend_recips = [ crypto.create_keypair()[0] for i in range(5) ]
    >>> connection = StaticConnection(my_keys, recipients=pretend_recips)
    >>> connection.recipients == pretend_recips
    True

    To specify mediators responsible for forwarding messages to the recipient:
    >>> pretend_mediators = [ crypto.create_keypair()[0] for i in range(5) ]
    >>> connection = StaticConnection(
    ...     my_keys, their_vk=their_pretend_verkey,
    ...     routing_keys=pretend_mediators
    ... )
    >>> connection.routing_keys == pretend_mediators
    True

    By default, `StaticConnection` will POST messages to the endpoint given
    over HTTP. You can, however, specify an alternative `Send` method for
    `StaticConnection` as in the example below:
    >>> async def my_send(msg: bytes, endpoint: str) -> Optional[bytes]:
    ...     print('pretending to send message to', endpoint)
    ...     response = None
    ...     return response
    >>> connection = StaticConnection(
    ...     my_keys, their_vk=their_pretend_verkey,
    ...     endpoint='example.com', send=my_send
    ... )
    >>> connection.send({'@type': 'doc_uri/protocol/0.1/test'})
    pretending to send message to example.com


    Arguments:

        keys (tuple of bytes or str): A tuple of our public and private key.

    NamedArguments:

        their_vk (bytes or str): Specify "their" verification key for this
            connection. Specifies only one recipient. Mutually exclusive with
            recipients.

        recipients ([bytes or str]): Specify one or more recipients for this
            connection. Mutually exclusive with their_vk.

        routing_keys ([bytes or str]): Specify one or more mediators for this
            connection.

        send (Send): Specify the send method for this connection. See notes
            above for function signature.  Defaults to
            `aries_staticagent.utils.http_send`.

        dispatcher (aries_staticagent.dispatcher.Dispatcher): Specify a
            dispatcher for this connection.  Defaults to
            `aries_staticagent.dispatcher.Dispatcher`.
    """

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

        super().__init__(
            keys, endpoint=endpoint, their_vk=their_vk,
            recipients=recipients, routing_keys=routing_keys
        )

        self._dispatcher = dispatcher if dispatcher else Dispatcher()
        self._next: ConditionFutureMap = {}
        self._sessions: Set[Session] = set()
        self._send: Send = send if send else http_send

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
            forward_to = self.recipients[0]
            for routing_key in self.routing_keys:
                packed_message = crypto.pack_message(
                    forward_msg(to=forward_to, msg=packed_message).serialize(),
                    [routing_key],
                )
                forward_to = routing_key

        return json.dumps(packed_message).encode('ascii')

    @contextmanager
    def session(self, send: SessionSend):
        """Open a new session for this connection."""

        session = Session(send)
        self._sessions.add(session)
        yield session
        self._sessions.remove(session)

    def session_open(self) -> bool:
        """Check whether connection has sessions open."""
        return bool(self._sessions)

    async def send_to_session(
            self,
            message: bytes,
            thread: str = None
    ) -> bool:
        """Send a message to all sessions with a matching thread."""
        if not self._sessions:
            raise RuntimeError(
                'Cannot send message to session; no open sessions'
            )

        sent = False
        for session in self._sessions:
            if not session.returning():
                continue

            if session.thread == thread or session.thread_all():
                await session.send(message)
                sent = True
        return sent

    async def handle(self, packed_message: bytes, session: Session = None):
        """Unpack and dispatch message to handler."""
        msg = self.unpack(packed_message)
        if session:
            session.update_thread_from_msg(msg)

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
        if not isinstance(msg, Message):
            if isinstance(msg, dict):
                msg = Message(msg)
            else:
                raise TypeError('msg must be type Message or dict')

        # TODO: Don't specify return route on messages sent to sessions?
        if return_route:
            if '~transport' not in msg:
                msg['~transport'] = {}
            msg['~transport']['return_route'] = return_route

        packed_message = self.pack(
            msg, anoncrypt=anoncrypt, plaintext=plaintext
        )

        if self.session_open():
            if await self.send_to_session(packed_message, msg.thread['thid']):
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
            timeout: int = None
    ) -> Message:
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
            timeout: int = None
    ):
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
