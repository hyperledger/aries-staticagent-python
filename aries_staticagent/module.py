""" Module base class """

from abc import ABC, abstractclassmethod
from functools import partial
from typing import Callable, Dict, Iterable, Mapping, Union

from .type import Type


class PartialType:
    """Class containing the type information of a route before having the
    context of the module as is the case when statically defining routes in
    a module definition.
    """

    __slots__ = ("doc_uri", "protocol", "version", "name")

    def __init__(
        self, name: str, doc_uri: str = None, protocol: str = None, version: str = None
    ):
        self.name = name
        self.version = version
        self.protocol = protocol
        self.doc_uri = doc_uri

    def complete(self, mod: "Module") -> Type:
        """Return a complete type given the module context."""
        doc_uri = self.doc_uri if self.doc_uri else type(mod).doc_uri
        protocol = self.protocol if self.protocol else type(mod).protocol
        version = self.version if self.version else type(mod).version
        if doc_uri is None:
            raise TypeError("doc_uri must be str")
        if protocol is None:
            raise TypeError("protocol must be str")
        if version is None:
            raise TypeError("version must be str")
        return Type(doc_uri, protocol, version, self.name)


class ModuleRouter(Mapping[Union[PartialType, Type], Callable]):
    """Collect module routes."""

    def __init__(self):
        self._routes: Dict[Union[Type, PartialType], Callable] = {}

    def __getitem__(self, item: Type) -> Callable:
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
            type_or_func: Union[Callable, str, Type] = args[0]
            if callable(type_or_func):
                func = type_or_func
                self._routes[PartialType(func.__name__)] = func
                return func

            if isinstance(type_or_func, str):
                msg_type_str = type_or_func

                def _route_from_str(func):
                    self._routes[Type.from_str(msg_type_str)] = func
                    return func

                return _route_from_str

            if isinstance(type_or_func, Type):
                msg_type = type_or_func

                def _route_from_type(func):
                    self._routes[msg_type] = func
                    return func

                return _route_from_type

        if kwargs:

            def _route_from_kwargs(func):
                name = kwargs.get("name", func.__name__)
                del kwargs["name"]
                self._routes[PartialType(name, **kwargs)] = func
                return func

            return _route_from_kwargs

        raise ValueError(
            "Expecting @route before a function or @route(msg_type) "
            "before a function!"
        )


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
        doc_uri = doc_uri if doc_uri is not None else self.doc_uri
        protocol = protocol if protocol is not None else self.protocol
        version = version if version is not None else self.version
        if doc_uri is None:
            raise TypeError("doc_uri must be str")
        if protocol is None:
            raise TypeError("protocol must be str")
        if version is None:
            raise TypeError("version must be str")
        return Type(doc_uri, protocol, version, name)

    def _finish_routes(self) -> Mapping[Type, Callable]:
        routes = {}
        for typ, handler in self.route.items():
            if isinstance(typ, PartialType):
                msg_type = typ.complete(self)
            elif isinstance(typ, Type):
                msg_type = typ
            else:
                raise TypeError(
                    f"Route of invaild type registered on module {type(self).__name__}"
                )
            routes[msg_type] = partial(handler, self)
        return routes

    @property
    def routes(self) -> Mapping[Type, Callable]:
        """Get the routes statically defined for this module and
        save in instance.
        """
        if self._routes is None:
            self._routes = self._finish_routes()
        return self._routes
