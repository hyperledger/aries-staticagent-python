""" Test Dispatcher """
import asyncio
from collections import namedtuple
import pytest

from aries_staticagent.dispatcher import (
    Dispatcher,
    NoRegisteredHandlerException,
)
from aries_staticagent.message import Message, MsgType

MockMessage = namedtuple("MockMessage", ["type", "test"])


def test_clear():
    """Test clearing handlers from dispatcher."""
    dispatcher = Dispatcher()
    dispatcher.add_handlers(
        {
            MsgType("doc;protocol/1.0/name"): lambda msg: msg,
            MsgType("doc;protocol/2.0/name"): lambda msg: msg,
        }
    )
    assert dispatcher.handlers
    dispatcher.clear_handlers()
    assert not dispatcher.handlers


@pytest.mark.asyncio
async def test_dispatching():
    """Test that routing works in agent."""
    dispatcher = Dispatcher()

    called_event = asyncio.Event()

    async def route_gets_called(_msg, **kwargs):
        kwargs["event"].set()

    dispatcher.add_handler(MsgType("test_protocol/1.0/testing_type"), route_gets_called)

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/1.0/testing_type", "test": "test"}
    )
    await dispatcher.dispatch(test_msg, event=called_event)

    assert called_event.is_set()


@pytest.mark.asyncio
async def test_dispatching_no_handler():
    """Test that routing works in agent."""
    dispatcher = Dispatcher()

    async def route_gets_called(_msg):
        pass

    dispatcher.add_handler(MsgType("test_protocol/1.0/testing_type"), route_gets_called)

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/4.0/other_type", "test": "test"}
    )
    with pytest.raises(NoRegisteredHandlerException):
        await dispatcher.dispatch(test_msg)


@pytest.mark.asyncio
async def test_dispatching_selection():
    """Test that routing works in agent."""
    dispatcher = Dispatcher()

    called_event = asyncio.Event()

    async def route_gets_called(_msg, **kwargs):
        kwargs["event"].set()

    async def route_not_called(_msg, **_kwargs):
        print("this should not be called")

    dispatcher.add_handler(
        MsgType("test_protocol/2.0/testing_type"),
        route_gets_called,
    )
    dispatcher.add_handler(
        MsgType("test_protocol/1.0/testing_type"),
        route_not_called,
    )

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/2.0/testing_type", "test": "test"}
    )
    await dispatcher.dispatch(test_msg, event=called_event)

    assert called_event.is_set()


@pytest.mark.asyncio
async def test_dispatching_selection_no_appropriate_handler():
    """Test that routing works in agent."""
    dispatcher = Dispatcher()

    dispatcher.add_handler(
        MsgType("test_protocol/2.0/testing_type"),
        lambda msg: msg,
    )
    dispatcher.add_handler(
        MsgType("test_protocol/1.0/testing_type"),
        lambda msg: msg,
    )

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/5.0/testing_type", "test": "test"}
    )
    with pytest.raises(NoRegisteredHandlerException):
        await dispatcher.dispatch(test_msg)


@pytest.mark.asyncio
async def test_dispatching_selection_message_too_old():
    """Test that routing works in agent."""
    dispatcher = Dispatcher()

    dispatcher.add_handler(MsgType("test_protocol/3.0/testing_type"), lambda msg: msg)
    dispatcher.add_handler(MsgType("test_protocol/2.0/testing_type"), lambda msg: msg)

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/1.0/testing_type", "test": "test"}
    )
    with pytest.raises(NoRegisteredHandlerException):
        await dispatcher.dispatch(test_msg)
