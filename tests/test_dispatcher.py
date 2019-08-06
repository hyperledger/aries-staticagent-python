""" Test Dispatcher """
import asyncio
from collections import namedtuple
import pytest

from aries_staticagent.dispatcher import (
    Dispatcher,
    Handler,
    NoRegisteredHandlerException
)
from aries_staticagent.message import Message

MockMessage = namedtuple('MockMessage', ['type', 'test'])


@pytest.mark.asyncio
async def test_good_handler():
    """ Test handler creation and run. """
    called_event = asyncio.Event()

    async def test(msg, **kwargs):
        assert msg == 'test'
        kwargs['event'].set()

    handler = Handler(
        test,
        doc_uri='',
        protocol='test_protocol',
        version='1.0',
        name='testing_type'
    )
    await handler.run('test', event=called_event)
    assert called_event.is_set()


@pytest.mark.asyncio
async def test_good_handler_from_type():
    """ Test handler creation from a type string. """
    called_event = asyncio.Event()

    async def test(msg, **kwargs):
        assert msg == 'test'
        kwargs['event'].set()

    handler = Handler(
        test,
        type='test_protocol/1.0/testing_type'
    )
    await handler.run('test', event=called_event)
    assert called_event.is_set()


@pytest.mark.asyncio
async def test_bad_handler():
    """ Test malformed handler creation raises ValueError """
    with pytest.raises(ValueError):
        Handler(lambda: print('blah'), doc_uri='')


@pytest.mark.asyncio
async def test_dispatching():
    """ Test that routing works in agent. """
    dispatcher = Dispatcher()

    called_event = asyncio.Event()

    async def route_gets_called(_msg, **kwargs):
        kwargs['event'].set()

    dispatcher.add_handler(Handler(
        route_gets_called, type='test_protocol/1.0/testing_type'
    ))

    test_msg = Message({
        '@type': 'test_protocol/1.0/testing_type', 'test': 'test'
    })
    await dispatcher.dispatch(test_msg, event=called_event)

    assert called_event.is_set()


@pytest.mark.asyncio
async def test_dispatching_selection():
    """ Test that routing works in agent. """
    dispatcher = Dispatcher()

    called_event = asyncio.Event()

    async def route_gets_called(_msg, **kwargs):
        kwargs['event'].set()

    async def route_not_called(_msg, **_kwargs):
        print('this should not be called')

    dispatcher.add_handler(Handler(
        route_gets_called, type='test_protocol/2.0/testing_type'
    ))
    dispatcher.add_handler(Handler(
        route_not_called, type='test_protocol/1.0/testing_type'
    ))

    test_msg = Message({
        '@type': 'test_protocol/2.0/testing_type', 'test': 'test'
    })
    await dispatcher.dispatch(test_msg, event=called_event)

    assert called_event.is_set()
