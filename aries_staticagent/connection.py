"""Static Agent Connection."""
import asyncio
from contextlib import asynccontextmanager, contextmanager
from functools import partial
import json
from typing import (
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)
import uuid

from . import crypto
from .dispatcher import Dispatcher, HandlerDispatcher, QueueDispatcher
from .dispatcher.queue_dispatcher import MsgQueue
from .message import Message, MsgType
from .module import Module
from .utils import ensure_key_bytes, forward_msg, http_send
from .operators import msg_type_is, is_reply_to


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

    THREAD_ALL = "all"

    def __init__(self, conn: "Connection", send: SessionSend, thread: str = None):
        if send is None:
            raise TypeError("Must supply send method to Session")

        if not callable(send) and not asyncio.iscoroutine(send):
            raise TypeError(
                "Invalid send method; expected coroutine or function, got {}".format(
                    type(send).__name__
                )
            )

        self._id = str(uuid.uuid4())
        self._conn = conn
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
        if "~transport" not in msg and self._thread is None:
            return

        transport = msg["~transport"]
        if transport["return_route"] == "all":
            self._thread = self.THREAD_ALL
            return

        if transport["return_route"] == "thread":
            self._thread = transport["return_route_thread"]
            return

        if transport["return_route"] == "none":
            self._thread = None
            return

    def should_return_route(self) -> bool:
        """Session set to return route?"""
        return bool(self._thread)

    def thread_all(self) -> bool:
        """Session is set to return all messages."""
        return self.thread == self.THREAD_ALL

    async def send(self, message: bytes):
        """Send a packed message to this session."""
        if not self.should_return_route():
            raise RuntimeError("Session is not set to return route")

        ret = self._send(message)
        if asyncio.iscoroutine(ret):
            return await ret

        return ret

    async def handle(self, message: bytes):
        """
        Handle a message received over this session.

        Delegates to connection's handle.
        """
        return await self._conn.handle(message, self)

    def __hash__(self):
        return hash(self.session_id)

    def __eq__(self, other):
        if not isinstance(other, Session):
            return False
        return self.session_id == other.session_id


class Keys:
    Key = Union[bytes, str]

    """Container for keys with convenience methods."""

    class Mixin:
        """Mixin for shortcuts to keys."""

        def __init__(self, keys: "Keys"):
            self.keys = keys

        @property
        def verkey(self):
            """Get verkey."""
            return self.keys.verkey

        @property
        def verkey_b58(self):
            """Get Base58 encoded verkey."""
            return self.keys.verkey_b58

        @property
        def sigkey(self):
            """Get sigkey."""
            return self.keys.sigkey

        @property
        def did(self):
            """Get verkey based DID for this connection."""
            return self.keys.did

    def __init__(self, verkey: Key, sigkey: Key):
        self._verkey = ensure_key_bytes(verkey)
        self._sigkey = ensure_key_bytes(sigkey)

    @property
    def verkey(self):
        """Get verkey."""
        return self._verkey

    @property
    def verkey_b58(self):
        """Get Base58 encoded verkey."""
        return crypto.bytes_to_b58(self.verkey)

    @property
    def sigkey(self):
        """Get sigkey."""
        return self._sigkey

    @property
    def did(self):
        """Get verkey based DID for this connection."""
        return crypto.bytes_to_b58(self._verkey[:16])

    def __str__(self):
        return "Keys({}, {}...)".format(
            self.verkey_b58, crypto.bytes_to_b58(self.sigkey)[:10]
        )


class Target:
    """Container for information about our message destination."""

    def __init__(
        self,
        *,
        endpoint: str = None,
        their_vk: Union[bytes, str] = None,
        recipients: Sequence[Union[bytes, str]] = None,
        routing_keys: Sequence[Union[bytes, str]] = None,
    ):
        if their_vk and recipients:
            raise ValueError("their_vk and recipients are mutually exclusive.")

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
        **_kwargs,
    ):
        """Update their information."""
        if their_vk and recipients:
            raise ValueError("their_vk and recipients are mutually exclusive.")

        if endpoint:
            self.endpoint = endpoint

        if their_vk:
            self.recipients = [ensure_key_bytes(their_vk)]

        if recipients:
            self.recipients = list(map(ensure_key_bytes, recipients))

        if routing_keys:
            self.routing_keys = list(map(ensure_key_bytes, routing_keys))


class Connection(Keys.Mixin):
    """Create a Static Agent Connection to another agent.

    The following will create a Static Connection with just the receiving end
    in place. This makes it possible to receive a message over this connection
    without yet knowing where messages will be sent.

    >>> my_keys = crypto.create_keypair()
    >>> connection = Connection.receiver(my_keys)

    To create a Static Agent Connection with both ends configured:
    >>> their_pretend_verkey = crypto.create_keypair()[0]
    >>> connection = Connection.from_parts(
    ...     my_keys, their_vk=their_pretend_verkey
    ... )

    Or, when there are multiple recipients:
    >>> pretend_recips = [ crypto.create_keypair()[0] for i in range(5) ]
    >>> connection = Connection.from_parts(
    ...     my_keys, recipients=pretend_recips
    ... )

    To specify mediators responsible for forwarding messages to the recipient:
    >>> pretend_mediators = [ crypto.create_keypair()[0] for i in range(5) ]
    >>> connection = Connection.from_parts(
    ...     my_keys, their_vk=their_pretend_verkey,
    ...     routing_keys=pretend_mediators
    ... )

    By default, `Connection` will POST messages to the endpoint given
    over HTTP. You can, however, specify an alternative `Send` method for
    `Connection` as in the example below:
    >>> async def my_send(msg: bytes, endpoint: str) -> Optional[bytes]:
    ...     print('pretending to send message to', endpoint)
    ...     response = None
    ...     return response
    >>> connection = Connection.from_parts(
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

    DEFAULT_TIMEOUT = 5

    def __init__(
        self,
        keys: Keys,
        target: Target = None,
        *,
        modules: Sequence[Union[Module, type]] = None,
        send: Send = None,
        dispatcher: HandlerDispatcher = None,
    ):

        Keys.Mixin.__init__(self, keys)
        self.target = target

        if modules:
            for mod in modules:
                if isinstance(mod, type):  # attempt to instantiate module
                    mod = mod()
                self.route_module(mod)

        self._send: Send = send or http_send
        self._dispatcher: Dispatcher = dispatcher or HandlerDispatcher()
        self._router: HandlerDispatcher = self._dispatcher
        self._sessions: Set[Session] = set()

    @classmethod
    def from_parts(
        cls,
        keys: Union[Keys, Tuple[Keys.Key, Keys.Key]],
        *,
        endpoint: str = None,
        their_vk: Union[bytes, str] = None,
        recipients: Sequence[Union[bytes, str]] = None,
        routing_keys: Sequence[Union[bytes, str]] = None,
        **kwargs,
    ):
        """Construct a static connection from its parts.

        Arguments:

            keys (tuple of bytes or str): A tuple of our public and private
            key.

        NamedArguments:

            their_vk (bytes or str): Specify "their" verification key for this
                connection. Specifies only one recipient. Mutually exclusive
                with recipients.

            recipients ([bytes or str]): Specify one or more recipients for
                this connection. Mutually exclusive with their_vk.

            routing_keys ([bytes or str]): Specify one or more mediators for
                this connection.

            send (Send): Specify the send method for this connection. See notes
                above for function signature.  Defaults to
                `aries_staticagent.utils.http_send`.

            dispatcher (aries_staticagent.dispatcher.Dispatcher): Specify a
                dispatcher for this connection.  Defaults to
                `aries_staticagent.dispatcher.Dispatcher`.
        """
        if not isinstance(keys, Keys):
            keys = Keys(*keys)
        target = None
        if endpoint or their_vk or recipients or routing_keys:
            target = Target(
                endpoint=endpoint,
                their_vk=their_vk,
                recipients=recipients,
                routing_keys=routing_keys,
            )
        return cls(keys, target, **kwargs)

    @classmethod
    def receiver(cls, keys: Union[Keys, Tuple[Keys.Key, Keys.Key]], **kwargs):
        """Create a static connection to be used only for receiving messages.

        Arguments:

            keys (Keys or Tuple of keys): Our public and private keys.
        """
        if not isinstance(keys, Keys):
            keys = Keys(*keys)
        return cls(keys, **kwargs)

    @classmethod
    def random(cls, target: Target = None, **kwargs):
        """Generate connection with random keys."""
        return cls(Keys(*crypto.create_keypair()), target, **kwargs)

    @classmethod
    def from_seed(cls, seed: bytes, target: Target = None, **kwargs):
        """Generate connection from seed."""
        return cls(Keys(*crypto.create_keypair(seed=seed)), target, **kwargs)

    def route(self, msg_type: str) -> Callable:
        """Register route decorator."""

        def register_route_dec(func):
            self._router.add(MsgType(msg_type), func)
            return func

        return register_route_dec

    def route_module(self, module: Module):
        """Register a module for routing."""
        return self._router.extend(module.routes)

    def clear_routes(self):
        """Clear registered routes."""
        return self._router.clear()

    async def dispatch(self, message):
        """
        Dispatch message to handler.
        """
        await self._dispatcher.dispatch(message, self)

    @asynccontextmanager
    async def queue(self, condition: Callable[[Message], bool] = None):
        """Temporarily queue messages for awaiting, bypassing regular dispatch.

        All messages not claimed are processed through registerd handlers on exit.
        """
        original = self._dispatcher
        queue = MsgQueue(condition=condition, dispatcher=original)
        queue_dispatcher = QueueDispatcher(queue=queue)
        self._dispatcher = queue_dispatcher
        try:
            yield queue
        finally:
            await queue.flush()
            self._dispatcher = original

    def unpack(self, packed_message: Union[bytes, dict]) -> Message:
        """Unpack a message, filling out metadata in the MTC."""
        try:
            (unpacked_msg, sender_vk, recip_vk) = crypto.unpack_message(
                packed_message, self.verkey, self.sigkey
            )
            msg = Message.deserialize(unpacked_msg)
            if sender_vk:
                msg.mtc.set_authcrypted(sender_vk, recip_vk)
            else:
                msg.mtc.set_anoncrypted(recip_vk)

        except (ValueError, KeyError):
            if not isinstance(packed_message, bytes):
                raise TypeError(
                    "Expected bytes, got {}".format(type(packed_message).__name__)
                )
            msg = Message.deserialize(packed_message)
            msg.mtc.set_plaintext()

        return msg

    def pack(
        self, msg: Union[dict, Message], anoncrypt=False, plaintext=False
    ) -> bytes:
        """Pack a message for sending over the wire."""
        if plaintext and anoncrypt:
            raise ValueError("plaintext and anoncrypt flags are mutually exclusive.")

        if not isinstance(msg, Message):
            if isinstance(msg, dict):
                msg = Message.parse_obj(msg)
            else:
                raise TypeError(
                    f"msg must be type Message or dict; received {type(msg)}"
                )

        if plaintext:
            return msg.serialize().encode("ascii")

        if not self.target or not self.target.recipients:
            raise RuntimeError("No recipients for whom to pack this message")

        if anoncrypt:
            packed_message = crypto.pack_message(
                msg.serialize(),
                self.target.recipients,
            )
        else:
            packed_message = crypto.pack_message(
                msg.serialize(),
                self.target.recipients,
                self.verkey,
                self.sigkey,
            )

        if self.target.routing_keys:
            forward_to = self.target.recipients[0]
            for routing_key in self.target.routing_keys:
                packed_message = crypto.pack_message(
                    forward_msg(to=forward_to, msg=packed_message).serialize(),
                    [routing_key],
                )
                forward_to = routing_key

        return json.dumps(packed_message).encode("ascii")

    @contextmanager
    def session(self, send: SessionSend):
        """Open a new session for this connection."""

        session = Session(self, send)
        self._sessions.add(session)
        yield session
        self._sessions.remove(session)

    def session_open(self) -> bool:
        """Check whether connection has sessions open."""
        return bool(self._sessions)

    async def send_to_session(self, message: bytes, thread: str = None) -> bool:
        """Send a message to all sessions with a matching thread."""
        if not self._sessions:
            raise RuntimeError("Cannot send message to session; no open sessions")

        sent = False
        for session in self._sessions:
            if not session.should_return_route():
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

        await self.dispatch(msg)

    async def send_async(
        self,
        msg: Union[dict, Message],
        *,
        return_route: str = None,
        plaintext: bool = False,
        anoncrypt: bool = False,
    ):
        """
        Send a message to the agent connected through this Connection.
        """
        if not isinstance(msg, Message):
            if isinstance(msg, dict):
                msg = Message.parse_obj(msg)
            else:
                raise TypeError(
                    f"msg must be type Message or dict; received {type(msg)}"
                )

        # TODO: Don't specify return route on messages sent to sessions?
        if return_route:
            msg = msg.with_transport(return_route=return_route)

        packed_message = self.pack(msg, anoncrypt=anoncrypt, plaintext=plaintext)

        if self.session_open():
            if await self.send_to_session(packed_message, msg.thread["thid"]):
                return

        if not self.target or not self.target.endpoint:
            raise MessageDeliveryError(
                msg="Cannot send message; no endpoint and no return route."
            )

        try:
            response = await self._send(packed_message, self.target.endpoint)
        except Exception as err:
            raise MessageDeliveryError(msg=str(err)) from err

        if response:
            if return_route is None or return_route == "none":
                raise RuntimeError("Response received when no response was expected")
            await self.handle(response)

    async def send_and_await_reply_async(
        self,
        msg: Union[dict, Message],
        *,
        return_route: str = "all",
        plaintext: bool = False,
        anoncrypt: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Message:
        """Send a message and wait for a reply to that message."""
        hydrated = Message.parse_obj(msg) if not isinstance(msg, Message) else msg
        return await self.send_and_await_returned_async(
            hydrated,
            condition=partial(is_reply_to, hydrated),
            return_route=return_route,
            plaintext=plaintext,
            anoncrypt=anoncrypt,
            timeout=timeout,
        )

    async def send_and_await_returned_async(
        self,
        msg: Union[dict, Message],
        *,
        type_: str = None,
        condition: Callable[[Message], bool] = None,
        return_route: str = "all",
        plaintext: bool = False,
        anoncrypt: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Message:
        """Send a message and wait for a message to be returned."""
        if type_:
            condition = partial(msg_type_is, type_)

        async with self.queue(condition=condition) as queue:
            await self.send_async(
                msg, return_route=return_route, plaintext=plaintext, anoncrypt=anoncrypt
            )
            return await queue.get(timeout=timeout)

    async def await_message(
        self,
        *,
        type_: str = None,
        condition: Callable[[Message], bool] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Wait for a message.

        Note that it's possible for a message to arrive just before or during
        the setup of this function. If it's likely that a message will arrive
        as a result of an action taken prior to calling await_message, use the
        `next` context manager instead.
        """
        if type_:
            condition = partial(msg_type_is, type_)

        async with self.queue(condition=condition) as queue:
            return await queue.get(timeout=timeout)

    def send(self, *args, **kwargs):
        """Blocking wrapper around send_async."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.send_async(*args, **kwargs))

    def send_and_await_reply(self, *args, **kwargs) -> Message:
        """Blocking wrapper around send_and_await_reply_async."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.send_and_await_reply_async(*args, **kwargs))

    def send_and_await_returned(self, *args, **kwargs) -> Message:
        """Blocking wrapper around send_and_await_reply_async."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.send_and_await_returned_async(*args, **kwargs)
        )
