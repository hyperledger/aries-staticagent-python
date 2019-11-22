"""Test StaticConection send method."""
import asyncio
import copy
from functools import partial
from asyncio import wait_for

import pytest

from aries_staticagent import (
    StaticConnection, Message, MessageDeliveryError, crypto
)

# pylint: disable=redefined-outer-name

MESSAGE = Message({
    '@type': 'doc;protocol/1.0/name'
})
RESPONSE = Message({
    '@type': 'doc;protocol/1.0/response'
})


@pytest.fixture(scope='module')
def alice_keys():
    """Alice's keys."""
    return StaticConnection.Keys(*crypto.create_keypair())


@pytest.fixture(scope='module')
def bob_keys():
    """Bob's keys."""
    return StaticConnection.Keys(*crypto.create_keypair())

@pytest.fixture
def alice_gen(alice_keys, bob_keys):
    def _gen(send=None, dispatcher=None):
        return StaticConnection(
            alice_keys,
            their_vk=bob_keys.verkey,
            endpoint='asdf',
            send=send,
            dispatcher=dispatcher
        )
    return _gen

@pytest.fixture
def alice(alice_gen):
    return alice_gen()

@pytest.fixture
def bob_gen(alice_keys, bob_keys):
    def _gen(send=None, dispatcher=None):
        return StaticConnection(
            bob_keys,
            their_vk=alice_keys.verkey,
            endpoint='asdf',
            send=send,
            dispatcher=dispatcher
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

        async def __call__(
                self, msg, _endpoint, _response_handler, _error_handler):
            self.sent_message = msg

        async def call_response(
                self, response, msg, _endpoint, response_handler,
                _error_handler):
            self.sent_message = msg
            await response_handler(response)

        async def call_error(
                self, msg, _endpoint, _response_handler, error_handler):
            self.sent_message = msg
            await error_handler('error')


    return _Send()

@pytest.fixture
def reply():
    """Mock send callable."""
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
async def test_send_simple(alice_gen, bob_gen, send):
    """Test simple send."""
    alice = alice_gen(send)
    bob = bob_gen(send)

    await alice.send_async(MESSAGE)
    assert bob.unpack(send.sent_message) == MESSAGE


@pytest.mark.asyncio
async def test_no_endpoint_or_reply_raises_error(alice_gen, bob, send):
    """Test no return route or endpoint or reply raises error."""
    alice = alice_gen(send)
    alice.endpoint = ''
    with pytest.raises(MessageDeliveryError):
        await alice.send_async(MESSAGE)


@pytest.mark.asyncio
async def test_outbound_return_route_set(alice_gen, bob, send):
    """Test no return route or endpoint or reply raises error."""
    alice = alice_gen(send)

    new_msg = copy.deepcopy(MESSAGE)
    await alice.send_async(new_msg, return_route='all')
    sent = bob.unpack(send.sent_message)
    assert '~transport' in sent
    assert 'return_route' in sent['~transport']
    assert sent['~transport']['return_route'] == 'all'

    new_msg = copy.deepcopy(MESSAGE)
    new_msg['~transport'] = {}
    await alice.send_async(new_msg, return_route='all')
    sent = bob.unpack(send.sent_message)
    assert '~transport' in sent
    assert 'return_route' in sent['~transport']
    assert sent['~transport']['return_route'] == 'all'


@pytest.mark.asyncio
async def test_reply_works(alice, bob, reply):
    """Test reply mechanism."""
    with alice.reply_handler(reply):
        await alice.send_async(MESSAGE)
    assert bob.unpack(reply.replied) == MESSAGE


@pytest.mark.asyncio
async def test_response_handler(alice_gen, bob, send, dispatcher):
    """Test response handler works."""
    alice = alice_gen(
        partial(send.call_response, bob.pack(RESPONSE)),
        dispatcher
    )
    await alice.send_async(MESSAGE, return_route='all')
    assert bob.unpack(send.sent_message) == MESSAGE
    assert dispatcher.dispatched == RESPONSE


@pytest.mark.asyncio
async def test_response_handler_no_return_route_raises_error(
        alice_gen, bob, send, dispatcher):
    """Test response handler works."""
    alice = alice_gen(
        partial(send.call_response, bob.pack(RESPONSE)),
        dispatcher
    )
    with pytest.raises(RuntimeError):
        await alice.send_async(MESSAGE)


@pytest.mark.asyncio
async def test_error_handler(alice_gen, bob, send):
    """Test error handler works."""
    alice = alice_gen(send.call_error)
    with pytest.raises(MessageDeliveryError, match='error'):
        await alice.send_async(MESSAGE)


@pytest.mark.asyncio
async def test_claim_next_messages(alice_gen, bob, dispatcher):
    """Test holding and awaiting messages."""
    alice = alice_gen(dispatcher=dispatcher)
    bob_msg = bob.pack(MESSAGE)
    with alice.next() as message:
        await alice.handle(bob_msg)
        assert await wait_for(message, 1) == MESSAGE


@pytest.mark.asyncio
async def test_next_raises_error_on_bad_condition(alice):
    """Bad condition raises error."""
    with pytest.raises(TypeError):
        with alice.next(condition='asdf'):
            pass


@pytest.mark.asyncio
async def test_next_condition(alice_gen, bob, dispatcher):
    """Test hold condtions."""
    alice = alice_gen(dispatcher=dispatcher)
    with alice.next(
            condition=lambda msg: msg.type == MESSAGE.type
    ) as message:
        await alice.handle(bob.pack(MESSAGE))
        assert dispatcher.dispatched is None
        assert await wait_for(message, 1) == MESSAGE
        await alice.handle(bob.pack(RESPONSE))
        assert dispatcher.dispatched == RESPONSE
    assert not alice._next


@pytest.mark.asyncio
async def test_next_type(alice_gen, bob, dispatcher):
    """Test hold condtions."""
    alice = alice_gen(dispatcher=dispatcher)
    with alice.next(MESSAGE.type) as message:
        await alice.handle(bob.pack(MESSAGE))
        assert dispatcher.dispatched is None
        assert await wait_for(message, 1) == MESSAGE
        await alice.handle(bob.pack(RESPONSE))
        assert dispatcher.dispatched == RESPONSE
    assert not alice._next


@pytest.mark.asyncio
async def test_multiple_next_fulfilled_sequentially(alice, bob):
    """Test all matching next condtions are fulfilled."""
    with alice.next(MESSAGE.type) as next_of_type, \
            alice.next() as next_anything:
        await alice.handle(bob.pack(MESSAGE))
        first = await wait_for(next_of_type, 1)
        await alice.handle(bob.pack(MESSAGE))
        second = await wait_for(next_anything, 1)
        assert first == second


@pytest.mark.asyncio
async def test_next_with_type_and_cond_raises_error(alice):
    """Test value error raised when both type and condition specified."""
    with pytest.raises(ValueError):
        with alice.next(MESSAGE.type, lambda msg: True):
            pass


@pytest.mark.asyncio
async def test_send_and_await_reply(alice_gen, bob, send):
    """Test holding and awaiting messages."""
    alice = alice_gen(partial(send.call_response, bob.pack(RESPONSE)))
    response = await alice.send_and_await_reply_async(MESSAGE)
    assert response == RESPONSE


@pytest.mark.asyncio
async def test_await_message(alice, bob):
    """Test awaiting a message."""
    waiting_task = asyncio.ensure_future(alice.await_message())
    await asyncio.sleep(.1)
    await alice.handle(bob.pack(MESSAGE))
    message = await waiting_task
    assert message == MESSAGE


def test_blocking_send(alice_gen, bob, send):
    """Test blocking send"""
    alice = alice_gen(send=send)
    alice.send(MESSAGE)
    assert bob.unpack(send.sent_message) == MESSAGE


def test_blocking_send_and_await_reply(alice_gen, bob, send):
    """Test blocking send and await reply"""
    alice = alice_gen(send=partial(send.call_response, bob.pack(RESPONSE)))
    response = alice.send_and_await_reply(MESSAGE)
    assert response == RESPONSE
