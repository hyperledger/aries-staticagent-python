""" Test routing functions of Connection. """

from aries_staticagent.module import ModuleRouter
import asyncio
import pytest
from aries_staticagent import Connection, Message, Module
from aries_staticagent.dispatcher import Dispatcher, NoRegisteredHandlerException
from aries_staticagent.message import MsgType

# pylint: disable=redefined-outer-name
# pylint: disable=too-few-public-methods


@pytest.fixture
def dispatcher():
    """Function scoped dispatcher fixture"""
    yield Dispatcher()


@pytest.fixture
def conn(dispatcher):
    """Function scoped static connection fixture. This connection isn't
    actually connected to anything.
    """
    yield Connection.from_parts((b"", b""), dispatcher=dispatcher)


@pytest.fixture
def event():
    """Function scoped event fixture. Useful for verifying that an event occurs
    in an asynchronous function.
    """
    yield asyncio.Event()


@pytest.mark.asyncio
async def test_simple_route(event, dispatcher, conn):
    """Test using route decorator on a method."""

    @conn.route("test_protocol/1.0/testing_type")
    async def test(msg, **kwargs):  # pylint: disable=unused-variable
        assert msg["test"] == "test"
        kwargs["event"].set()

    await dispatcher.dispatch(
        Message.parse_obj({"@type": "test_protocol/1.0/testing_type", "test": "test"}),
        event=event,
    )

    assert event.is_set()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "route_args, route_kwargs, send_type",
    [
        (["test_protocol/1.0/testing_type"], {}, "test_protocol/1.0/testing_type"),
        (
            [MsgType("test_protocol/1.0/testing_type")],
            {},
            "test_protocol/1.0/testing_type",
        ),
        ([], {"name": "not_testing_type"}, "test_protocol/1.0/not_testing_type"),
        (
            [],
            {"name": "not_testing_type", "protocol": "not_test_protocol"},
            "not_test_protocol/1.0/not_testing_type",
        ),
        (
            [],
            {
                "name": "not_testing_type",
                "protocol": "not_test_protocol",
                "version": "2.0",
            },
            "not_test_protocol/2.0/not_testing_type",
        ),
        (
            [],
            {
                "name": "not_testing_type",
                "protocol": "not_test_protocol",
                "version": "2.0",
                "doc_uri": "doc;",
            },
            "doc;not_test_protocol/2.0/not_testing_type",
        ),
    ],
)  # pylint: disable=too-many-arguments
async def test_routing_module_explicit_def(
    event, dispatcher, conn, route_args, route_kwargs, send_type
):
    """Test that routing to a module works."""

    class TestModule(Module):
        """Simple module for testing"""

        doc_uri = ""
        protocol = "test_protocol"
        version = "1.0"
        route = ModuleRouter()

        @route(*route_args, **route_kwargs)
        async def route_gets_called(self, _msg, **kwargs):
            """Test that this method is called"""
            kwargs["event"].set()

    mod = TestModule()
    conn.route_module(mod)

    test_msg = Message.parse_obj({"@type": send_type, "test": "test"})
    await dispatcher.dispatch(test_msg, event=event)

    assert event.is_set()


@pytest.mark.asyncio
async def test_routing_module_simple(event, dispatcher, conn):
    """Test that routing to a module works."""

    class TestModule(Module):
        """Simple module for testing"""

        doc_uri = ""
        protocol = "test_protocol"
        version = "1.0"
        route = ModuleRouter()

        @route
        async def testing_type(self, _msg, **kwargs):
            """Test that this method is called"""
            kwargs["event"].set()

    mod = TestModule()
    conn.route_module(mod)

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/1.0/testing_type", "test": "test"}
    )
    await dispatcher.dispatch(test_msg, event=event)

    assert event.is_set()


@pytest.mark.asyncio
async def test_routing_many(event, dispatcher, conn):
    """Test that routing to a module works."""
    dispatcher.called_module = None

    class TestModule1(Module):
        """Simple module for testing"""

        doc_uri = ""
        protocol = "test_protocol"
        version = "1.0"
        route = ModuleRouter()

        @route
        async def testing_type(self, _msg, **kwargs):
            """Test that this method is called"""
            kwargs["dispatcher"].called_module = 1
            kwargs["event"].set()

    class TestModule2(Module):
        """Simple module for testing"""

        doc_uri = ""
        protocol = "test_protocol"
        version = "2.0"
        route = ModuleRouter()

        @route
        async def testing_type(self, _msg, **kwargs):
            """Test that this methodis called"""
            kwargs["dispatcher"].called_module = 2
            kwargs["event"].set()

    conn.route_module(TestModule1())
    conn.route_module(TestModule2())

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/1.0/testing_type", "test": "test"}
    )
    await dispatcher.dispatch(test_msg, event=event, dispatcher=dispatcher)
    await event.wait()

    assert event.is_set()
    assert dispatcher.called_module == 1

    event.clear()

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/2.0/testing_type", "test": "test"}
    )
    await dispatcher.dispatch(test_msg, event=event, dispatcher=dispatcher)
    await event.wait()

    assert event.is_set()
    assert dispatcher.called_module == 2

    assert dispatcher.handlers
    conn.clear_routes()
    assert not dispatcher.handlers


@pytest.mark.asyncio
async def test_routing_no_matching_version(event, dispatcher, conn):
    """Test error raised on no matching handlers."""

    class TestModule(Module):
        """Simple module for testing"""

        doc_uri = ""
        protocol = "test_protocol"
        version = "1.0"
        route = ModuleRouter()

        @route
        async def testing_type(self, _msg, **kwargs):
            """Test that this method is called"""
            kwargs["event"].set()

    mod = TestModule()
    conn.route_module(mod)

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/3.0/testing_type", "test": "test"}
    )
    with pytest.raises(NoRegisteredHandlerException):
        await dispatcher.dispatch(test_msg, event=event)


@pytest.mark.asyncio
async def test_routing_minor_version_different(event, dispatcher, conn):
    """Test routing when minor version is different."""

    class TestModule(Module):
        """Simple module for testing"""

        doc_uri = ""
        protocol = "test_protocol"
        version = "1.4"
        route = ModuleRouter()

        @route
        async def testing_type(self, _msg, **kwargs):
            """Test that this method is called"""
            kwargs["event"].set()

    mod = TestModule()
    conn.route_module(mod)

    test_msg = Message.parse_obj(
        {"@type": "test_protocol/1.0/testing_type", "test": "test"}
    )
    await dispatcher.dispatch(test_msg, event=event)

    assert event.is_set()
