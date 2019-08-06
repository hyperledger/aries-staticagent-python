""" Module base class """

from typing import Union, Callable
from .utils import Semver


def route(type_or_func: Union[Callable, str]):
    """ Route definition decorator
        if just @route is used, type_or_func is the decorated function
        if @route(type) is used, type_or_func is the type string.
    """
    if callable(type_or_func):
        func = type_or_func
        func.handler_for = None
        return func

    if isinstance(type_or_func, str):
        msg_type = type_or_func

        def _route(func):
            func.handler_for = msg_type
            return func

        return _route

    raise ValueError(
        'Expecting @route before a function or @route(msg_type) '
        'before a function!'
    )


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

    _normalized_version = None
    _version_info = None

    @property
    def version(cls):
        """ Convenience property: access VERSION """
        return cls.VERSION

    @property
    def normalized_version(cls):
        """ Convenience property: get normalized version info string """
        if not cls._normalized_version:
            version_info = cls.version_info
            cls._normalized_version = str(version_info)
        return cls._normalized_version

    @property
    def version_info(cls):
        """ Convenience property: get version info (major, minor, patch, etc.)
        """
        if not cls._version_info:
            cls._version_info = Semver.from_str(cls.VERSION)
        return cls._version_info

    @property
    def protocol(cls):
        """ Convenience property: access PROTOCOL """
        return cls.PROTOCOL

    @property
    def doc_uri(cls):
        """ Convenience property: access DOC_URI """
        return cls.DOC_URI

    @property
    def qualified_protocol(cls):
        """ Convenience property: build qualified protocol identifier """
        return cls.DOC_URI + cls.PROTOCOL

    @property
    def protocol_identifer_uri(cls):
        """ Convenience property: build full protocol identifier """
        return cls.qualified_protocol + '/' + cls.normalized_version


class Module(metaclass=MetaModule):  # pylint: disable=too-few-public-methods
    """ Base Module class """
    DOC_URI = None
    PROTOCOL = None
    VERSION = None

    def __init__(self):
        self._routes = None

    def type(self, name):
        """ Build a type string for this module. """
        return '{}{}/{}/{}'.format(
            self.__class__.doc_uri,
            self.__class__.protocol,
            self.__class__.version,
            name
        )

    def _find_routes(self):
        found = {}
        for key in dir(self):
            if key == 'routes' or key.startswith('__'):
                continue
            val = getattr(self, key)
            if hasattr(val, 'handler_for'):
                msg_type = val.handler_for
                if msg_type is None:
                    msg_type = self.type(key)
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
