""" Define Message base class. """
import json
import re
import uuid

from .utils import Semver


class InvalidMessage(Exception):
    """ Thrown when message is malformed. """


MTURI_RE = re.compile(r'(.*?)([a-z0-9._-]+)/(\d[^/]*)/([a-z0-9._-]+)$')


def generate_id():
    """ Generate a message id. """
    return str(uuid.uuid4())


def parse_type_info(message_type_uri):
    """ Parse message type for doc_uri, portocol, version, and short type.
    """
    matches = MTURI_RE.match(message_type_uri)
    if not matches:
        raise InvalidMessage('Invalid message type')

    return matches.groups()


class Message(dict):
    """ Message base class.
        Inherits from UserDict meaning it behaves like a dictionary.
    """
    __slots__ = (
        'mtc',
        'doc_uri',
        'protocol',
        'version',
        'version_info',
        'short_type'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if '@type' not in self:
            raise InvalidMessage('No @type in message')

        if '@id' not in self:
            self['@id'] = generate_id()
        elif not isinstance(self['@id'], str):
            raise InvalidMessage('Message @id is invalid; must be str')


        self.doc_uri, self.protocol, self.version, self.short_type = \
            parse_type_info(self.type)

        try:
            self.version_info = Semver.from_str(self.version)
        except ValueError as err:
            raise InvalidMessage('Invalid message type version') from err

    @property
    def type(self):
        """ Shortcut for msg['@type'] """
        return self['@type']

    @property
    def id(self):  # pylint: disable=invalid-name
        """ Shortcut for msg['@id'] """
        return self['@id']

    @property
    def qualified_protocol(self):
        """ Shortcut for constructing qualified protocol identifier from
            doc_uri and protocol
        """
        return self.doc_uri + self.protocol

    # Serialization
    @classmethod
    def deserialize(cls, serialized: str):
        """ Deserialize a message from a json string. """
        try:
            return cls(json.loads(serialized))
        except json.decoder.JSONDecodeError as err:
            raise InvalidMessage('Could not deserialize message') from err

    def serialize(self):
        """ Serialize a message into a json string. """
        return json.dumps(self)

    def pretty_print(self):
        """ return a 'pretty print' representation of this message. """
        return json.dumps(self, indent=2)
