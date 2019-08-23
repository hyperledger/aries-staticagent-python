""" Message and Module Type related classes and helpers. """
from functools import partial
from operator import is_not
from typing import Union
import re
from semver import VersionInfo, parse

MTURI_RE = re.compile(r'(.*?)([a-z0-9._-]+)/(\d[^/]*)/([a-z0-9._-]+)$')


class Semver(VersionInfo):  # pylint: disable=too-few-public-methods
    """ Wrapper around the more complete VersionInfo class from semver package.

        This wrapper enables abbreviated versions in message types
        (i.e. 1.0 not 1.0.0).
    """
    SEMVER_RE = re.compile(
        r'^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$'
    )

    @classmethod
    def from_str(cls, version_str):
        """ Parse version information from a string. """
        matches = Semver.SEMVER_RE.match(version_str)
        if matches:
            args = list(matches.groups())
            if not matches.group(3):
                args.append('0')
            return Semver(*map(int, filter(partial(is_not, None), args)))

        parts = parse(version_str)

        return cls(
            parts['major'],
            parts['minor'],
            parts['patch'],
            parts['prerelease'],
            parts['build']
        )


class InvalidType(Exception):
    """ When type is unparsable or invalid. """


class Type:
    """ Message and Module type container """
    FORMAT = '{}{}/{}/{}'

    __slots__ = (
        'doc_uri',
        'protocol',
        'version',
        'version_info',
        'name',
        '_normalized',
        '_str'
    )

    def __init__(
            self,
            doc_uri: str,
            protocol: str,
            version: Union[str, Semver],
            name: str):
        if isinstance(version, str):
            try:
                self.version_info = Semver.from_str(version)
            except ValueError as err:
                raise InvalidType(
                    'Invalid type version {}'.format(version)
                ) from err
            self.version = version
        elif isinstance(version, Semver):
            self.version_info = version
            self.version = str(version)
        else:
            raise InvalidType(
                '`version` must be instance of str or Semver,'
                ' got {}'.format(type(version).__name__)
            )

        self.doc_uri = doc_uri
        self.protocol = protocol
        self.name = name
        self._str = Type.FORMAT.format(
            self.doc_uri,
            self.protocol,
            self.version,
            self.name
        )
        self._normalized = Type.FORMAT.format(
            self.doc_uri,
            self.protocol,
            self.version_info,
            self.name
        )

    @classmethod
    def from_str(cls, type_str):
        """ Parse type from string. """
        matches = MTURI_RE.match(type_str)
        if not matches:
            raise InvalidType('Invalid message type')

        return cls(*matches.groups())

    def __str__(self):
        return self._str

    @property
    def normalized(self):
        """ Return the normalized string representation """
        return self._normalized

    def __hash__(self):
        return hash(self._normalized)

    def __eq__(self, other):
        if isinstance(other, Type):
            return self._normalized == other.normalized
        if isinstance(other, str):
            return self._normalized == other
        raise TypeError('Cannot compare Type and {}'.format(type(other)))

    def __ne__(self, other):
        return not self.__eq__(other)
