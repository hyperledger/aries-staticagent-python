""" Test agent core message module. """

import pytest

from aries_staticagent.message import Message, InvalidMessage
from aries_staticagent.type import Type, Semver, InvalidType

TEST_TYPE = "test_type/protocol/1.0/test"
TEST_TYPE_NO_DOC = "protocol/1.0/test"


def test_valid_message():
    """Test basic message creation and member access."""
    id_ = "12345"

    msg = Message({"@type": TEST_TYPE, "@id": id_})
    assert msg.type == TEST_TYPE
    assert msg.id == id_
    assert msg.doc_uri == "test_type/"
    assert msg.protocol == "protocol"
    assert msg.version == "1.0"
    assert msg.normalized_version == "1.0.0"
    assert msg.name == "test"
    assert msg.version_info == Semver(1, 0, 0)


def test_valid_message_no_doc_uri():
    """Test basic message creation and member access."""
    id_ = "12345"

    msg = Message({"@type": TEST_TYPE_NO_DOC, "@id": id_})
    assert msg.type == TEST_TYPE_NO_DOC
    assert msg.id == id_
    assert msg.doc_uri == ""
    assert msg.protocol == "protocol"
    assert msg.version == "1.0"
    assert msg.normalized_version == "1.0.0"
    assert msg.name == "test"
    assert msg.version_info == Semver(1, 0, 0)


def test_valid_message_with_type_obj():
    """Test creating message using Type object."""
    id_ = "12345"

    msg = Message({"@type": Type.from_str(TEST_TYPE), "@id": id_})
    assert msg.type == TEST_TYPE
    assert msg.id == id_
    assert msg.doc_uri == "test_type/"
    assert msg.protocol == "protocol"
    assert msg.version == "1.0"
    assert msg.normalized_version == "1.0.0"
    assert msg.name == "test"
    assert msg.version_info == Semver(1, 0, 0)


def test_id_generated():
    """Test ID is generated for message where one is not specified."""
    msg = Message({"@type": TEST_TYPE})
    assert msg.type == TEST_TYPE
    assert msg.id is not None


def test_message_serialization():
    """Test deserializing and serializing a message"""
    msg = Message.deserialize('{"@type": "%s"}' % TEST_TYPE)
    assert msg.type == TEST_TYPE
    assert msg.id is not None
    assert msg.doc_uri == "test_type/"
    assert msg.protocol == "protocol"
    assert msg.version == "1.0"
    assert msg.name == "test"
    assert msg.version_info == Semver(1, 0, 0)

    assert msg.serialize() == '{"@type": "%s", "@id": "%s"}' % (TEST_TYPE, msg.id)


def test_bad_serialized_message():
    """Test bad serialized message raises an error on deserialze."""
    with pytest.raises(InvalidMessage):
        Message.deserialize("asdf")


def test_bad_message_no_type():
    """Test no type in message raises error."""
    with pytest.raises(InvalidMessage):
        Message({"test": "test"})


def test_pretty_print():
    """Assert pretty print is returning something crazy."""
    assert isinstance(Message({"@type": TEST_TYPE}).pretty_print(), str)


@pytest.mark.parametrize(
    "type_str",
    [
        "bad",
        "",
        "doc_uri/protocol",
        "doc_uri/protocol/1.0",
        # 'protocol/1.0/type',  # doc_uri can be nothing
        "doc_uri//1.0/type",
        "doc_uri/protocol/version/type",
    ],
)
def test_bad_message_type(type_str):
    """Test bad message types raise InvalidMessage"""
    with pytest.raises(InvalidType):
        Message({"@type": type_str})


@pytest.mark.parametrize("id_", [12345, {"id": "12345"}, [1, 2, 3, 4, 5]])
def test_bad_message_id(id_):
    """Test message with bad message id"""
    with pytest.raises(InvalidMessage):
        Message({"@type": TEST_TYPE, "@id": id_})
