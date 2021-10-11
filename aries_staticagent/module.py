""" Module base class """

from abc import ABC
from functools import partial
from typing import (
    Callable,
    ClassVar,
    Dict,
    Iterable,
    Mapping,
    TypeVar,
    Union,
    cast,
)

from .message import MsgType, ProtocolIdentifier


RouteFunc = TypeVar("RouteFunc", bound=Callable)


class ModuleRouter(Mapping[MsgType, Callable]):
    """Collect module routes."""

    def __init__(
        self,
        protocol: Union[str, ProtocolIdentifier],
    ):
        if not isinstance(protocol, ProtocolIdentifier):
            protocol = ProtocolIdentifier(protocol)
        self.protocol = protocol
        self._routes: Dict[Union[str, MsgType], Callable] = {}

    def __getitem__(self, item: Union[str, MsgType]) -> Callable:
        return self._routes[item]

    def __iter__(self) -> Iterable:
        return iter(self._routes)

    def __len__(self):
        return len(self._routes)

    def route(
        self,
        func_or_name: Union[RouteFunc, str] = None,
        *,
        doc_uri: str = None,
        protocol: str = None,
        version: str = None,
        name: str = None,
        msg_type: Union[str, MsgType] = None
    ) -> Union[Callable[..., RouteFunc], RouteFunc]:
        """Decorator for defining routes within a module.

        This decorator can be used in a few different ways, as demonstrated by
        the following examples:

        >>> router = ModuleRouter("doc/protocol/1.0")
        >>> @router
        ... def test():
        ...     pass
        >>> assert "doc/protocol/1.0/test" in router
        >>> assert router["doc/protocol/1.0/test"] == test
        >>>
        >>> @router("alt-name")
        ... def test1():
        ...     pass
        >>> assert "doc/protocol/1.0/alt-name" in router
        >>> assert router["doc/protocol/1.0/alt-name"] == test1
        >>>
        >>> @router(msg_type="another-doc/some-protocol/2.0/name")
        ... def test2():
        ...     pass
        >>> assert "another-doc/some-protocol/2.0/name" in router
        >>> assert router["another-doc/some-protocol/2.0/name"] == test2
        >>>
        >>> @router(doc_uri="another-doc/")
        ... def test3():
        ...     pass
        >>> assert "another-doc/protocol/1.0/test3" in router
        >>> assert router["another-doc/protocol/1.0/test3"] == test3
        >>> @router(protocol="some-protocol")
        ... def test4():
        ...     pass
        >>> assert "doc/some-protocol/1.0/test4" in router
        >>> assert router["doc/some-protocol/1.0/test4"] == test4
        >>>
        >>> @router(version="2.0")
        ... def test5():
        ...     pass
        >>> assert "doc/protocol/2.0/test5" in router
        >>> assert router["doc/protocol/2.0/test5"] == test5
        >>>
        >>> @router(name="another-alt-name")
        ... def test6():
        ...     pass
        >>> assert "doc/protocol/1.0/another-alt-name" in router
        >>> assert router["doc/protocol/1.0/another-alt-name"] == test6
        """

        if not func_or_name:
            return lambda f: cast(
                RouteFunc,
                self.route(
                    f,
                    doc_uri=doc_uri,
                    protocol=protocol,
                    version=version,
                    name=name,
                    msg_type=msg_type,
                ),
            )
        if isinstance(func_or_name, str):
            name = func_or_name
            return lambda f: cast(
                RouteFunc,
                self.route(
                    f,
                    doc_uri=doc_uri,
                    protocol=protocol,
                    version=version,
                    name=name,
                    msg_type=msg_type,
                ),
            )
        if not isinstance(func_or_name, Callable):
            raise TypeError("func is not a callable")

        func: Callable = func_or_name
        if msg_type:
            if isinstance(msg_type, str):
                msg_type = MsgType(msg_type)
            self._routes[MsgType(msg_type)] = func
            return func

        type_to_route = MsgType.unparse(
            doc_uri=doc_uri or self.protocol.doc_uri or "",
            protocol=protocol or self.protocol.protocol or "",
            version=version or self.protocol.version or "",
            name=name or func.__name__ or "",
        )
        self._routes[MsgType(type_to_route)] = func
        return func

    def __call__(self, *args, **kwargs):
        """Route definition decorator."""
        return self.route(*args, **kwargs)

    def contextualize(self, context: object) -> Dict[MsgType, Callable]:
        return {
            msg_type: partial(handler, context) for msg_type, handler in self.items()
        }


class Module(ABC):  # pylint: disable=too-few-public-methods
    """Base Module class."""

    protocol: ClassVar[str]
    route: ClassVar[ModuleRouter]

    def __init__(self):
        self._routes = None
        self._protocol_identifier = ProtocolIdentifier(self.protocol)

    @property
    def protocol_identifier(self) -> ProtocolIdentifier:
        return self._protocol_identifier

    @property
    def router(self) -> ModuleRouter:
        """Alias to route."""
        return self.route

    @property
    def doc_uri(self) -> str:
        return self.protocol_identifier.doc_uri

    @property
    def protocol_name(self) -> str:
        return self.protocol_identifier.protocol

    @property
    def version(self) -> str:
        return self.protocol_identifier.version

    def type(
        self, name: str, doc_uri: str = None, protocol: str = None, version: str = None
    ):
        """Build a type string for this module."""
        # doc_url can be falsey, need explicit none check
        doc_uri = doc_uri if doc_uri is not None else self.doc_uri
        protocol = protocol or self.protocol_name
        version = version or self.version
        return MsgType.unparse(doc_uri, protocol, version, name)

    def _contextualize_routes(self) -> Mapping[MsgType, Callable]:
        return self.router.contextualize(context=self)

    @property
    def routes(self) -> Mapping[MsgType, Callable]:
        """Get the routes statically defined for this module and
        save in instance.
        """
        if self._routes is None:
            self._routes = self._contextualize_routes()
        return self._routes
