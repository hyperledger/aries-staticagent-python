""" Test module module """
from typing import Callable, cast
from aries_staticagent.message import MsgType
import pytest

from aries_staticagent.module import Module, ModuleRouter, PartialType


def test_module_def():
    """Test module creationg and special attributes of module"""

    class TestModule(Module):
        """Simple module for testing"""

        DOC_URI = "test_doc_uri/"
        PROTOCOL = "test_protocol"
        VERSION = "1.0"


def test_module_missing_attrs():
    """Test that defining a module without required attributes raises
    an error.
    """
    # pylint: disable=unused-variable

    with pytest.raises(TypeError):

        class TestModule1(Module):
            """Simple module for testing"""

            doc_uri = "test_doc_uri/"
            protocol = "test_protocol"

        print(TestModule1().version)

    with pytest.raises(TypeError):

        class TestModule2(Module):
            """Simple module for testing"""

            doc_uri = "test_doc_uri/"
            version = "1.0"

        TestModule2()

    with pytest.raises(TypeError):

        class TestModule3(Module):
            """Simple module for testing"""

            protocol = "test_protocol"
            version = "1.0"

        TestModule3()


def test_routes_construction():
    """Test that module routes are properly constructed."""

    class TestModule(Module):
        """Simple module for testing"""

        doc_uri = "test_doc_uri/"
        protocol = "test_protocol"
        version = "1.0"
        route = ModuleRouter()

        @route
        async def test(self, msg):
            """This should create a route"""

        @route
        async def test1(self, msg):
            """This should create another route"""

    mod = TestModule()
    assert mod.routes
    assert len(TestModule.route)
    assert "test_doc_uri/test_protocol/1.0/test" in mod.routes
    assert "test_doc_uri/test_protocol/1.0/test1" in mod.routes


def test_module_type_helper():
    """Test that module routes are properly constructed."""

    class TestModule(Module):
        """Simple module for testing"""

        doc_uri = "test_doc_uri/"
        protocol = "test_protocol"
        version = "1.0"
        route = ModuleRouter()

    mod = TestModule()
    assert mod.type("test") == "test_doc_uri/test_protocol/1.0/test"
    assert mod.type("test", doc_uri="") == "test_protocol/1.0/test"
    assert mod.type("test", protocol="protocol") == "test_doc_uri/protocol/1.0/test"
    assert mod.type("test", version="2.0") == "test_doc_uri/test_protocol/2.0/test"


def test_route_bad_input():
    """Test that calling route directly with bad inputs raises error."""
    with pytest.raises(ValueError):
        route = ModuleRouter()
        route([1, 2, "garbage"])


def test_module_router_decorator():
    routes = ModuleRouter()

    @routes
    def test0():
        pass

    @routes
    def test1():
        pass

    test_type = MsgType.unparse("", "protocol", "1.0", "test")

    @routes(test_type)
    def test2():
        pass

    @routes("doc/protocol/1.0/test")
    def test3():
        pass

    @routes(protocol="test", name="test4")
    def test4():
        pass

    assert PartialType(name="test0") in routes
    assert PartialType(name="test1") in routes
    assert test_type in routes
    assert "doc/protocol/1.0/test" in routes
    assert MsgType("doc/protocol/1.0/test") in routes
    assert PartialType(protocol="test", name="test4") in routes

    for route in iter(routes):
        assert route

    assert routes.complete(doc_uri="doc/", protocol="test", version="1.0")
    with pytest.raises(TypeError):
        routes._routes[cast(MsgType, None)] = cast(Callable, None)
        routes.complete(doc_uri="doc/", protocol="test", version="1.0")
