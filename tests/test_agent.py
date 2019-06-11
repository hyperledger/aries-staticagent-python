""" Test Agent """
import asyncio
from collections import namedtuple
import pytest

from aries_staticagent.agent import Agent, NoRegisteredRouteException
from aries_staticagent.module import module, route_def
from aries_staticagent.messages import Message

MockMessage = namedtuple('MockMessage', ['type', 'test'])

@pytest.mark.asyncio
async def test_routing():
    """ Test that routing works in agent. """
    agent = Agent()

    called_event = asyncio.Event()

    @agent.route('testing_type')
    async def route_gets_called(agent, msg, **kwargs):
        kwargs['event'].set()

    test_msg = MockMessage('testing_type', 'test')
    await agent.handle(test_msg, event=called_event)

    assert called_event.is_set()

@pytest.mark.asyncio
async def test_module_routing_explicit_def():
    """ Test that routing to a module works. """

    agent = Agent()
    called_event = asyncio.Event()

    @module
    class TestModule():
        DOC_URI = ''
        PROTOCOL = 'test_protocol'
        VERSION = '1.0'

        routes = {}

        @route_def(routes, 'test_protocol/1.0/testing_type')
        async def route_gets_called(self, agent, msg, **kwargs):
            kwargs['event'].set()

    mod = TestModule()
    agent.route_module(mod)

    test_msg = Message({'@type': 'test_protocol/1.0/testing_type', 'test': 'test'})
    await agent.handle(test_msg, event=called_event)

    assert called_event.is_set()

@pytest.mark.asyncio
async def test_module_routing_simple():
    """ Test that routing to a module works. """
    agent = Agent()
    called_event = asyncio.Event()

    @module
    class TestModule():
        DOC_URI = ''
        PROTOCOL = 'test_protocol'
        VERSION = '1.0'

        async def testing_type(self, agent, msg, *args, **kwargs):
            kwargs['event'].set()

    mod = TestModule()
    agent.route_module(mod)

    test_msg = Message({'@type': 'test_protocol/1.0/testing_type', 'test': 'test'})
    await agent.handle(test_msg, event=called_event)

    assert called_event.is_set()

@pytest.mark.asyncio
async def test_module_routing_many():
    """ Test that routing to a module works. """
    agent = Agent()
    agent.called_module = None
    routed_event = asyncio.Event()

    @module
    class TestModule1():
        DOC_URI = ''
        PROTOCOL = 'test_protocol'
        VERSION = '1.0'

        async def testing_type(self, agent, msg, *args, **kwargs):
            agent.called_module = 1
            kwargs['event'].set()

    @module
    class TestModule2():
        DOC_URI = ''
        PROTOCOL = 'test_protocol'
        VERSION = '2.0'

        async def testing_type(self, agent, msg, *args, **kwargs):
            agent.called_module = 2
            kwargs['event'].set()

    agent.route_module(TestModule1())
    agent.route_module(TestModule2())

    test_msg = Message({'@type': 'test_protocol/1.0/testing_type', 'test': 'test'})
    await agent.handle(test_msg, event=routed_event)
    await routed_event.wait()

    assert routed_event.is_set()
    assert agent.called_module == 1

    routed_event.clear()

    test_msg = Message({'@type': 'test_protocol/2.0/testing_type', 'test': 'test'})
    await agent.handle(test_msg, event=routed_event)
    await routed_event.wait()

    assert routed_event.is_set()
    assert agent.called_module == 2

@pytest.mark.asyncio
async def test_module_routing_no_matching_version():
    """ Test that routing to a module works. """
    agent = Agent()
    called_event = asyncio.Event()

    @module
    class TestModule():
        DOC_URI = ''
        PROTOCOL = 'test_protocol'
        VERSION = '1.0'

        async def testing_type(self, agent, msg, *args, **kwargs):
            kwargs['event'].set()

    mod = TestModule()
    agent.route_module(mod)

    test_msg = Message({'@type': 'test_protocol/3.0/testing_type', 'test': 'test'})
    with pytest.raises(NoRegisteredRouteException):
        await agent.handle(test_msg, event=called_event)

@pytest.mark.asyncio
async def test_module_routing_minor_version_different():
    """ Test that routing to a module works. """
    agent = Agent()
    called_event = asyncio.Event()

    @module
    class TestModule():
        DOC_URI = ''
        PROTOCOL = 'test_protocol'
        VERSION = '1.4'

        async def testing_type(self, agent, msg, *args, **kwargs):
            kwargs['event'].set()

    mod = TestModule()
    agent.route_module(mod)

    test_msg = Message({'@type': 'test_protocol/1.0/testing_type', 'test': 'test'})
    await agent.handle(test_msg, event=called_event)

    assert called_event.is_set()
