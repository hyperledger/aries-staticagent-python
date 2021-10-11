""" Define Message base class. """
from abc import ABC
from functools import partial
from operator import is_not
import re
from typing import Any, ClassVar, Mapping, Optional, Type, TypeVar, Union
from uuid import uuid4

from pydantic import BaseModel, Extra, Field
from pydantic.class_validators import validator
from semver import VersionInfo

from .mtc import MessageTrustContext


class MsgVersion(VersionInfo):  # pylint: disable=too-few-public-methods
    """Wrapper around the more complete VersionInfo class from semver package.

    This wrapper enables abbreviated versions in message types
    (i.e. 1.0 not 1.0.0).
    """

    SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$")

    @classmethod
    def from_str(cls, version_str):
        """Parse version information from a string."""
        matches = cls.SEMVER_RE.match(version_str)
        if matches:
            args = list(matches.groups())
            if not matches.group(3):
                args.append("0")
            return cls(*map(int, filter(partial(is_not, None), args)))

        parts = VersionInfo.parse(version_str)

        return cls(
            parts.major,
            parts.minor,
            parts.patch,
            parts.prerelease,
            parts.build,
        )


class InvalidProtocolIdentifier(ValueError):
    """Raised when protocol identifier is unparsable or invalid."""


class ProtocolIdentifier(str):
    """Protocol identifier."""

    PIURI_RE = re.compile(r"^(.*?)([a-z0-9._-]+)/(\d[^/]*)/?$")

    def __init__(self, ident: str):
        """Parse Protocol Identifier string."""
        super().__init__()
        matches = self.PIURI_RE.match(ident)
        if not matches:
            raise InvalidProtocolIdentifier(f"Invalid protocol identifier: {ident}")
        doc_uri, protocol, version = matches.groups()
        try:
            self.version_info = MsgVersion.from_str(version)
        except ValueError as err:
            raise InvalidProtocolIdentifier(
                f"Invalid protocol version {version}"
            ) from err

        self.version = version
        self.doc_uri = doc_uri
        self.protocol = protocol
        self.normalized = f"{self.doc_uri}{self.protocol}/{self.version_info}"
        self.normalized_version = str(self.version_info)

    @classmethod
    def unparse(cls, doc_uri: str, protocol: str, version: str):
        return cls(f"{doc_uri}{protocol}/{version}")


class InvalidType(ValueError):
    """When type is unparsable or invalid."""


class MsgType(str):
    """Message type."""

    MTURI_RE = re.compile(r"^(.*?)([a-z0-9._-]+)/(\d[^/]*)/([a-z0-9._-]+)$")

    def __init__(self, msg_type: str):
        """Parse Message Type string."""
        super().__init__()
        matches = self.MTURI_RE.match(msg_type)
        if not matches:
            raise InvalidType(f"Invalid message type: {msg_type}")

        doc_uri, protocol, version, name = matches.groups()
        try:
            self.version_info = MsgVersion.from_str(version)
        except ValueError as err:
            raise InvalidType(f"Invalid message type version {version}") from err

        self.version = version
        self.doc_uri = doc_uri
        self.protocol = protocol
        self.name = name
        self.normalized = (
            f"{self.doc_uri}{self.protocol}/{self.version_info}/{self.name}"
        )
        self.normalized_version = str(self.version_info)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: str):
        return cls(value)

    @classmethod
    def parse(cls, msg_type: str):
        return cls(msg_type)

    @classmethod
    def unparse(cls, doc_uri: str, protocol: str, version: str, name: str):
        return cls(f"{doc_uri}{protocol}/{version}/{name}")


MessageType = TypeVar("MessageType", bound="Message")


class Message(BaseModel, Mapping[str, Any]):

    type: MsgType = Field(alias="@type")
    id: str = Field(alias="@id", default_factory=lambda: str(uuid4()))
    _alias_dict: Mapping[str, Any] = {}
    _mtc: MessageTrustContext = MessageTrustContext()

    class Config:
        extra = Extra.allow
        allow_mutation = False
        underscore_attrs_are_private = True
        allow_population_by_field_name = True

    def __init__(self, **data):
        super().__init__(**data)
        self._alias_dict = self.dict(by_alias=True)

    def __getitem__(self, item: str) -> Any:
        return self._alias_dict[item]

    def __len__(self) -> int:
        return len(self.__dict__)

    @property
    def mtc(self):
        return self._mtc

    @property
    def thread(self):
        return self.get("~thread", {"thid": None})

    def with_transport(self: MessageType, return_route: str = None) -> MessageType:
        return type(self)(
            **{
                **self.dict(by_alias=True),
                "~transport": {"return_route": return_route} if return_route else {},
            }
        )

    def with_thread(self: MessageType, thread: Mapping[str, str]) -> MessageType:
        return type(self)(**{**self.dict(by_alias=True), "~thread": thread})

    @classmethod
    def deserialize(
        cls: Type[MessageType],
        serialized: Union[str, bytes],
        mtc: Optional[MessageTrustContext] = None,
    ) -> MessageType:
        """Deserialize a message from a json string."""
        msg = cls.parse_raw(serialized)
        if mtc:
            msg._mtc = mtc

        return msg

    def serialize(self, **kwargs) -> str:
        """Serialize a message into a json string."""
        return self.json(by_alias=True, exclude_none=True, **kwargs)

    def pretty_print(self) -> str:
        """return a 'pretty print' representation of this message."""
        return self.serialize(indent=2)


class BaseMessage(Message, ABC):

    msg_type: ClassVar[MsgType]
    type: Optional[MsgType] = Field(alias="@type")

    @validator("type", pre=True, always=True)
    @classmethod
    def _type(cls, value):
        """Set type if not present."""
        if not value:
            return cls.msg_type
        if value != cls.msg_type:
            raise ValueError(
                "Invalid message type for {}: {}".format(cls.__name__, value)
            )
        return value
