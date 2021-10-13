""" Test module module """
import pytest

from aries_staticagent.module import Module, ModuleRouter


def test_module_bad_protocol():
    """Test that defining a module without required attributes raises
    an error.
    """
    # pylint: disable=unused-variable

    with pytest.raises(ValueError):

        class TestModule1(Module):
            """Simple module for testing"""

            protocol = "bad protocol"

        TestModule1()


def test_routes_construction():
    """Test that module routes are properly constructed."""

    class TestModule(Module):
        """Simple module for testing"""

        protocol = "test_doc_uri/test_protocol/1.0"
        route = ModuleRouter(protocol)

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

        protocol = "test_doc_uri/test_protocol/1.0"
        route = ModuleRouter(protocol)

    mod = TestModule()
    assert mod.type("test") == "test_doc_uri/test_protocol/1.0/test"
    assert mod.type("test", doc_uri="") == "test_protocol/1.0/test"
    assert mod.type("test", protocol="protocol") == "test_doc_uri/protocol/1.0/test"
    assert mod.type("test", version="2.0") == "test_doc_uri/test_protocol/2.0/test"


def test_route_bad_input():
    """Test that calling route directly with bad inputs raises error."""
    with pytest.raises(TypeError):
        route = ModuleRouter("doc/protocol/1.0")
        route([1, 2, "garbage"])


def test_module_router_decorator():
    router = ModuleRouter("doc/protocol/1.0")

    @router
    def test():
        pass

    assert "doc/protocol/1.0/test" in router
    assert router["doc/protocol/1.0/test"] is test

    @router("alt-name")
    def test1():
        pass

    assert "doc/protocol/1.0/alt-name" in router
    assert router["doc/protocol/1.0/alt-name"] is test1

    @router(msg_type="another-doc/some-protocol/2.0/name")
    def test2():
        pass

    assert "another-doc/some-protocol/2.0/name" in router
    assert router["another-doc/some-protocol/2.0/name"] is test2

    @router(doc_uri="another-doc/")
    def test3():
        pass

    assert "another-doc/protocol/1.0/test3" in router
    assert router["another-doc/protocol/1.0/test3"] is test3

    @router(protocol="some-protocol")
    def test4():
        pass

    assert "doc/some-protocol/1.0/test4" in router
    assert router["doc/some-protocol/1.0/test4"] is test4

    @router(version="2.0")
    def test5():
        pass

    assert "doc/protocol/2.0/test5" in router
    assert router["doc/protocol/2.0/test5"] is test5

    @router(name="another-alt-name")
    def test6():
        pass

    assert "doc/protocol/1.0/another-alt-name" in router
    assert router["doc/protocol/1.0/another-alt-name"] is test6

    for route in iter(router):
        assert route
