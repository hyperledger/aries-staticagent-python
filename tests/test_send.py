"""Test StaticConection send method."""
import asyncio
import uuid
import copy
from functools import partial

import pytest

from aries_staticagent import (
    Connection,
    Keys,
    Message,
    MessageDeliveryError,
    crypto,
)
from aries_staticagent.connection import Session

# pylint: disable=redefined-outer-name


@pytest.fixture
def message():
    yield Message.parse_obj({"@type": "doc;protocol/1.0/name"})


@pytest.fixture
def response():
    yield Message.parse_obj({"@type": "doc;protocol/1.0/response"})


@pytest.fixture(scope="module")
def alice_keys():
    """Alice's keys."""
    return Keys(*crypto.create_keypair())


@pytest.fixture(scope="module")
def bob_keys():
    """Bob's keys."""
    return Keys(*crypto.create_keypair())


@pytest.fixture
def alice_gen(alice_keys, bob_keys):
    def _gen(send=None, dispatcher=None):
        return Connection.from_parts(
            alice_keys,
            their_vk=bob_keys.verkey,
            endpoint="asdf",
            send=send,
            dispatcher=dispatcher,
        )

    return _gen


@pytest.fixture
def alice(alice_gen):
    return alice_gen()


@pytest.fixture
def bob_gen(alice_keys, bob_keys):
    def _gen(send=None, dispatcher=None):
        return Connection.from_parts(
            bob_keys,
            their_vk=alice_keys.verkey,
            endpoint="asdf",
            send=send,
            dispatcher=dispatcher,
        )

    return _gen


@pytest.fixture
def bob(bob_gen):
    return bob_gen()


@pytest.fixture
def send():
    """Mock send callable."""

    class _Send:
        def __init__(self):
            self.sent_message = None

        async def __call__(self, msg, _endpoint):
            self.sent_message = msg

        async def return_response(self, response, msg, _endpoint):
            self.sent_message = msg
            return response

        async def raise_error(self, msg, _endpoint):
            self.sent_message = msg
            raise Exception("error")

    return _Send()


@pytest.fixture
def reply():
    """Mock reply callable."""

    class _Reply:
        def __init__(self):
            self.replied = None

        async def __call__(self, msg: bytes):
            self.replied = msg

    return _Reply()


@pytest.fixture
def dispatcher():
    class _Dispatcher:
        def __init__(self):
            self.dispatched = None

        async def dispatch(self, msg, conn):
            self.dispatched = msg

    return _Dispatcher()


@pytest.mark.asyncio
async def test_send_simple(alice_gen, bob_gen, send, message):
    """Test simple send."""
    alice = alice_gen(send)
    bob = bob_gen(send)

    await alice.send_async(message)
    assert bob.unpack(send.sent_message) == message


@pytest.mark.asyncio
async def test_no_endpoint_or_reply_raises_error(alice_gen, bob, send, message):
    """Test no return route or endpoint or reply raises error."""
    alice = alice_gen(send)
    alice.target.endpoint = ""
    with pytest.raises(MessageDeliveryError):
        await alice.send_async(message)


@pytest.mark.asyncio
async def test_outbound_return_route_set(alice_gen, bob, send, message):
    """Test no return route or endpoint or reply raises error."""
    alice = alice_gen(send)

    new_msg = copy.deepcopy(message)
    await alice.send_async(new_msg, return_route="all")
    sent = bob.unpack(send.sent_message)
    assert "~transport" in sent
    assert "return_route" in sent["~transport"]
    assert sent["~transport"]["return_route"] == "all"

    new_msg = copy.deepcopy(message)
    new_msg.with_transport()
    await alice.send_async(new_msg, return_route="all")
    sent = bob.unpack(send.sent_message)
    assert "~transport" in sent
    assert "return_route" in sent["~transport"]
    assert sent["~transport"]["return_route"] == "all"


@pytest.mark.asyncio
async def test_session_all(alice, bob, reply, message):
    """Test reply mechanism."""
    with alice.session(reply) as session:
        session._thread = Session.THREAD_ALL
        await alice.send_async(message)
    assert bob.unpack(reply.replied) == message


@pytest.mark.asyncio
async def test_session_thread(alice, bob, reply, message):
    """Test reply mechanism."""
    threaded_msg = copy.deepcopy(message)
    thread_id = str(uuid.uuid4())
    threaded_msg = threaded_msg.with_thread({"thid": thread_id})
    with alice.session(reply) as session:
        session._thread = thread_id
        await alice.send_async(threaded_msg)
    assert bob.unpack(reply.replied) == threaded_msg


@pytest.mark.asyncio
async def test_session_thread_all(alice, bob, reply, message):
    """Test reply mechanism."""
    threaded_msg = copy.deepcopy(message)
    thread_id = str(uuid.uuid4())
    threaded_msg = threaded_msg.with_thread({"thid": thread_id})
    thread_response = []
    with alice.session(reply) as session, alice.session(
        thread_response.append
    ) as thread_session:
        session._thread = Session.THREAD_ALL
        thread_session._thread = thread_id
        await alice.send_async(message)
        assert bob.unpack(reply.replied) == message
        assert not thread_response

        await alice.send_async(threaded_msg)
        assert bob.unpack(thread_response.pop()) == threaded_msg
        assert bob.unpack(reply.replied) == threaded_msg


@pytest.mark.asyncio
async def test_response_handler(alice_gen, bob, send, dispatcher, message, response):
    """Test response handler works."""
    alice = alice_gen(partial(send.return_response, bob.pack(response)), dispatcher)
    await alice.send_async(message, return_route="all")
    assert bob.unpack(send.sent_message) == message.with_transport(return_route="all")
    assert dispatcher.dispatched == response


@pytest.mark.asyncio
async def test_response_handler_no_return_route_raises_error(
    alice_gen, bob, send, dispatcher, message, response
):
    """Test response handler works."""
    alice = alice_gen(partial(send.return_response, bob.pack(response)), dispatcher)
    with pytest.raises(RuntimeError):
        await alice.send_async(message)


@pytest.mark.asyncio
async def test_error_handler(alice_gen, bob, send, message, response):
    """Test error handler works."""
    alice = alice_gen(send.raise_error)
    with pytest.raises(MessageDeliveryError, match="error"):
        await alice.send_async(message)


@pytest.mark.asyncio
async def test_claim_next_messages(alice_gen, bob, dispatcher, message):
    """Test holding and awaiting messages."""
    alice = alice_gen(dispatcher=dispatcher)
    bob_msg = bob.pack(message)
    async with alice.queue() as queue:
        await alice.handle(bob_msg)
        assert await queue.get(timeout=1) == message


@pytest.mark.asyncio
async def test_next_condition(alice_gen, bob, dispatcher, message, response):
    """Test hold condtions."""
    alice = alice_gen(dispatcher=dispatcher)
    async with alice.queue(condition=lambda msg: msg.type == message.type) as queue:
        await alice.handle(bob.pack(message))
        assert dispatcher.dispatched is None
        assert await queue.get(timeout=1) == message
        await alice.handle(bob.pack(response))
        assert dispatcher.dispatched == response
    assert not alice._next


@pytest.mark.asyncio
async def test_next_type(alice_gen, bob, dispatcher, message, response):
    """Test hold condtions."""
    alice = alice_gen(dispatcher=dispatcher)
    async with alice.queue() as queue:
        await alice.handle(bob.pack(message))
        assert dispatcher.dispatched is None
        assert await queue.with_type(message.type, timeout=1) == message
        await alice.handle(bob.pack(response))
    assert dispatcher.dispatched == response
    assert not alice._next


@pytest.mark.asyncio
async def test_multiple_next_fulfilled_sequentially(alice, bob, message):
    """Test all matching next condtions are fulfilled."""
    async with alice.queue() as queue:
        await alice.handle(bob.pack(message))
        first = await queue.with_type(message.type, timeout=1)
        await alice.handle(bob.pack(message))
        second = await queue.get(timeout=1)
        assert first == second


@pytest.mark.asyncio
async def test_send_and_await_returned(alice_gen, bob, send, message, response):
    """Test holding and awaiting messages."""
    alice = alice_gen(partial(send.return_response, bob.pack(response)))
    response = await alice.send_and_await_returned_async(message)
    assert response == response


@pytest.mark.asyncio
async def test_send_and_await_reply(alice_gen, bob, send, message, response):
    """Test holding and awaiting messages."""
    msg_with_id = copy.deepcopy(message)
    response_with_thid = copy.deepcopy(response)
    response_with_thid = response_with_thid.with_thread({"thid": msg_with_id.id})
    alice = alice_gen(partial(send.return_response, bob.pack(response_with_thid)))
    response = await alice.send_and_await_reply_async(msg_with_id)
    assert response == response_with_thid


@pytest.mark.asyncio
async def test_await_message(alice, bob, message):
    """Test awaiting a message."""
    waiting_task = asyncio.ensure_future(alice.await_message())
    await asyncio.sleep(0.1)
    await alice.handle(bob.pack(message))
    message = await waiting_task
    assert message == message


def test_blocking_send(alice_gen, bob, send, message):
    """Test blocking send"""
    alice = alice_gen(send=send)
    alice.send(message)
    assert bob.unpack(send.sent_message) == message


def test_blocking_send_and_await_returned(alice_gen, bob, send, message, response):
    """Test blocking send and await reply"""
    alice = alice_gen(send=partial(send.return_response, bob.pack(response)))
    response = alice.send_and_await_returned(message)
    assert response == response


def test_blocking_send_and_await_reply(alice_gen, bob, send, message, response):
    """Test holding and awaiting messages."""
    msg_with_id = copy.deepcopy(message)
    response_with_thid = copy.deepcopy(response)
    response_with_thid = response_with_thid.with_thread({"thid": msg_with_id.id})
    alice = alice_gen(partial(send.return_response, bob.pack(response_with_thid)))
    response = alice.send_and_await_reply(msg_with_id)
    assert response == response_with_thid
