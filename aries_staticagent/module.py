""" Module base class """

from abc import ABC, abstractclassmethod
from functools import partial
from typing import Callable, Dict, Iterable, Mapping, NamedTuple, Optional, Union

from .message import MsgType


class PartialType(NamedTuple):
    """Class containing the type information of a route before having the
    context of the module as is the case when statically defining routes in
    a module definition.
    """

    name: Optional[str] = None
    doc_uri: Optional[str] = None
    protocol: Optional[str] = None
    version: Optional[str] = None

    def complete(
        self,
        doc_uri: str = None,
        protocol: str = None,
        version: str = None,
        name: str = None,
    ) -> MsgType:
        """Return a complete type given the module context."""
        doc_uri = self.doc_uri or doc_uri or ""
        protocol = self.protocol or protocol or ""
        version = self.version or version or ""
        name = self.name or name or ""
        return MsgType.unparse(doc_uri, protocol, version, name)


class ModuleRouter(Mapping[Union[PartialType, MsgType], Callable]):
    """Collect module routes."""

    def __init__(self):
        self._routes: Dict[Union[MsgType, PartialType], Callable] = {}

    def __getitem__(self, item: MsgType) -> Callable:
        return self._routes[item]

    def __iter__(self) -> Iterable:
        return iter(self._routes)

    def __len__(self):
        return len(self._routes)

    def __call__(self, *args, **kwargs):
        """Route definition decorator.

        if just @route is used, type_or_func is the decorated function
        if @route(type) is used, type_or_func is the type string.
        """
        if args:
            type_or_func: Union[Callable, str, MsgType] = args[0]
            if callable(type_or_func):
                func = type_or_func
                self._routes[PartialType(name=func.__name__)] = func
                return func

            if isinstance(type_or_func, MsgType):
                msg_type = type_or_func

                def _route_from_type(func):
                    self._routes[msg_type] = func
                    return func

                return _route_from_type

            if isinstance(type_or_func, str):
                msg_type_str = type_or_func

                def _route_from_str(func):
                    self._routes[MsgType(msg_type_str)] = func
                    return func

                return _route_from_str

        if kwargs:

            def _route_from_kwargs(func):
                self._routes[PartialType(**kwargs)] = func
                return func

            return _route_from_kwargs

        raise ValueError(
            "Expecting @route before a function or @route(msg_type) "
            "before a function!"
        )

    def complete(
        self,
        doc_uri: str = None,
        protocol: str = None,
        version: str = None,
        name: str = None,
        context: object = None,
    ) -> Dict[MsgType, Callable]:
        routes = {}
        for msg_type, handler in self._routes.items():
            if isinstance(msg_type, PartialType):
                route_type = msg_type.complete(doc_uri, protocol, version, name)
            elif isinstance(msg_type, MsgType):
                route_type = msg_type
            else:
                raise TypeError(
                    f"Route of invaild type {type(msg_type).__name__} registered"
                )
            routes[route_type] = partial(handler, context) if context else handler
        return routes


class Module(ABC):  # pylint: disable=too-few-public-methods
    """Base Module class"""

    def __init__(self):
        self._routes = None

    @property
    @classmethod
    @abstractclassmethod
    def doc_uri(cls) -> str:
        """Return doc_uri of module."""

    @property
    @classmethod
    @abstractclassmethod
    def protocol(cls) -> str:
        """Return protocol of module."""

    @property
    @classmethod
    @abstractclassmethod
    def version(cls) -> str:
        """Return protocol of module."""

    @property
    @classmethod
    @abstractclassmethod
    def route(cls) -> ModuleRouter:
        """Return router for module."""

    def type(
        self, name: str, doc_uri: str = None, protocol: str = None, version: str = None
    ):
        """Build a type string for this module."""
        # doc_url can be falsey, need explicit none check
        doc_uri = doc_uri if doc_uri is not None else self.doc_uri
        protocol = protocol or self.protocol
        version = version or self.version
        return MsgType.unparse(doc_uri, protocol, version, name)

    def _finish_routes(self) -> Mapping[MsgType, Callable]:
        return self.route.complete(
            self.doc_uri, self.protocol, self.version, context=self
        )

    @property
    def routes(self) -> Mapping[MsgType, Callable]:
        """Get the routes statically defined for this module and
        save in instance.
        """
        if self._routes is None:
            self._routes = self._finish_routes()
        return self._routes
