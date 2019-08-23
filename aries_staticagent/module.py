""" Module base class """

from typing import Union, Callable
from .type import Type


class InvalidModule(Exception):
    """ Thrown when module is malformed. """


class MetaModule(type):
    """ MetaModule:
        Ensures Module classes are well formed and provides convenience methods
    """
    def __new__(cls, name, bases, dct):
        if 'DOC_URI' not in dct:
            raise InvalidModule('DOC_URI missing from module definition')
        if 'PROTOCOL' not in dct:
            raise InvalidModule("PROTOCOL missing from module definition")
        if 'VERSION' not in dct:
            raise InvalidModule('VERSION missing from module definition')

        return type.__new__(cls, name, bases, dct)


class Module(metaclass=MetaModule):  # pylint: disable=too-few-public-methods
    """ Base Module class """
    DOC_URI = None
    PROTOCOL = None
    VERSION = None

    def __init__(self):
        self._routes = None

    def type(
            self,
            name: str,
            doc_uri: str = None,
            protocol: str = None,
            version: str = None
                ):
        """ Build a type string for this module. """
        doc_uri = doc_uri if doc_uri is not None else self.__class__.DOC_URI
        protocol = protocol if protocol is not None else self.__class__.PROTOCOL
        version = version if version is not None else self.__class__.VERSION
        return Type(doc_uri, protocol, version, name)

    def _find_routes(self):
        found = {}
        for key in dir(self):
            if key == 'routes' or key.startswith('__'):
                continue
            val = getattr(self, key)
            if hasattr(val, 'handler_for'):
                msg_type = val.handler_for
                if isinstance(msg_type, PartialType):
                    msg_type = msg_type.complete(self)

                found[msg_type] = val

        return found

    @property
    def routes(self):
        """ Get the routes statically defined for this module and
            save in instance.
        """
        if self._routes is None:
            self._routes = self._find_routes()
        return self._routes


class PartialType():
    """ Class containing the type information of a route before having the
        context of the module as is the case when statically defining routes in
        a module definition.
    """
    __slots__ = (
        'doc_uri',
        'protocol',
        'version',
        'name'
    )

    def __init__(
            self,
            name: str,
            doc_uri: str = None,
            protocol: str = None,
            version: str = None
                ):
        self.name = name
        self.version = version
        self.protocol = protocol
        self.doc_uri = doc_uri

    def complete(self, mod: Module) -> Type:
        """ Return a complete type given the module context. """
        doc_uri = self.doc_uri if self.doc_uri else type(mod).DOC_URI
        protocol = self.protocol if self.protocol else type(mod).PROTOCOL
        version = self.version if self.version else type(mod).VERSION
        return Type(doc_uri, protocol, version, self.name)


def route(*args, **kwargs):
    """ Route definition decorator
        if just @route is used, type_or_func is the decorated function
        if @route(type) is used, type_or_func is the type string.
    """
    if args:
        type_or_func: Union[Callable, str, Type] = args[0]
        if callable(type_or_func):
            func = type_or_func
            func.handler_for = PartialType(func.__name__)
            return func

        if isinstance(type_or_func, str):
            msg_type = type_or_func

            def _route(func):
                func.handler_for = Type.from_str(msg_type)
                return func

            return _route

        if isinstance(type_or_func, Type):
            msg_type = type_or_func

            def _route(func):
                func.handler_for = msg_type
                return func

            return _route

    if kwargs:
        def _route(func):
            name = kwargs.get('name', func.__name__)
            del kwargs['name']
            func.handler_for = PartialType(name, **kwargs)
            return func

        return _route

    raise ValueError(
        'Expecting @route before a function or @route(msg_type) '
        'before a function!'
    )
