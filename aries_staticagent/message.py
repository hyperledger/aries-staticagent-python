""" Define Message base class. """
import json
import uuid
from typing import Optional, Union

from .type import Type, Semver
from .mtc import MessageTrustContext


def generate_id():
    """ Generate a message id. """
    return str(uuid.uuid4())


class InvalidMessage(Exception):
    """ Thrown when message is malformed. """


class Message(dict):
    """ Message base class.
        Inherits from dict meaning it behaves like a dictionary.
    """
    __slots__ = (
        'mtc',
        '_type'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if '@type' not in self:
            raise InvalidMessage('No @type in message')

        if '@id' not in self:
            self['@id'] = generate_id()
        elif not isinstance(self['@id'], str):
            raise InvalidMessage('Message @id is invalid; must be str')

        if isinstance(self['@type'], Type):
            self._type = self['@type']
            self['@type'] = str(self._type)
        else:
            self._type = Type.from_str(self.type)
        self.mtc: Optional[MessageTrustContext] = None

    @property
    def type(self):
        """ Shortcut for msg['@type'] """
        return self['@type']

    @property
    def id(self):  # pylint: disable=invalid-name
        """ Shortcut for msg['@id'] """
        return self['@id']

    @property
    def thread(self):
        """Shortcut to msg['~thread'], if present."""
        return self.get('~thread', {'thid': None})

    @property
    def doc_uri(self) -> str:
        """ Get type doc_uri """
        return self._type.doc_uri

    @property
    def protocol(self) -> str:
        """ Get type protocol """
        return self._type.protocol

    @property
    def version(self) -> str:
        """ Get type version """
        return self._type.version

    @property
    def version_info(self) -> Semver:
        """ Get type version info """
        return self._type.version_info

    @property
    def name(self) -> str:
        """ Get type name """
        return self._type.name

    @property
    def normalized_version(self) -> str:
        """ Get type normalized version """
        return str(self._type.version_info)

    # Serialization
    @classmethod
    def deserialize(cls, serialized: Union[str, bytes]) -> 'Message':
        """ Deserialize a message from a json string. """
        try:
            return cls(json.loads(serialized))
        except json.decoder.JSONDecodeError as err:
            raise InvalidMessage('Could not deserialize message') from err

    def serialize(self) -> str:
        """ Serialize a message into a json string. """
        return json.dumps(self)

    def pretty_print(self) -> str:
        """ return a 'pretty print' representation of this message. """
        return json.dumps(self, indent=2)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Message):
            return False

        return super().__eq__(other)

    def __hash__(self):
        return hash(self.id)
