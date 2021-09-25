""" Test agent core message module. """

from aries_staticagent.mtc import MessageTrustContext
import json

import pytest

from aries_staticagent.message import (
    BaseMessage,
    InvalidType,
    MsgType,
    MsgVersion,
    Message,
)

TEST_TYPE = "test_type/protocol/1.0/test"
TEST_TYPE_NO_DOC = "protocol/1.0/test"


def test_valid_message():
    """Test basic message creation and member access."""
    id_ = "12345"

    msg = Message.parse_obj({"@type": TEST_TYPE, "@id": id_})
    assert msg.type == TEST_TYPE
    assert msg.id == id_
    assert msg.type.doc_uri == "test_type/"
    assert msg.type.protocol == "protocol"
    assert msg.type.version == "1.0"
    assert msg.type.normalized_version == "1.0.0"
    assert msg.type.name == "test"
    assert msg.type.version_info == MsgVersion(1, 0, 0)
    assert len(msg) == 2


def test_id_generated():
    """Test ID is generated for message where one is not specified."""
    msg = Message.parse_obj({"@type": TEST_TYPE})
    assert msg.type == TEST_TYPE
    assert msg.id is not None


def test_message_serialization():
    """Test deserializing and serializing a message"""
    msg = Message.deserialize(
        json.dumps({"@type": TEST_TYPE}), mtc=MessageTrustContext()
    )
    assert msg.type == TEST_TYPE
    assert msg.id is not None
    assert msg.mtc

    assert msg.serialize() == json.dumps({"@type": TEST_TYPE, "@id": msg.id})


def test_bad_serialized_message():
    """Test bad serialized message raises an error on deserialze."""
    with pytest.raises(ValueError):
        Message.deserialize("asdf")


def test_bad_message_no_type():
    """Test no type in message raises error."""
    with pytest.raises(ValueError):
        Message.parse_obj({"test": "test"})


def test_pretty_print():
    """Assert pretty print is returning something crazy."""
    assert isinstance(Message.parse_obj({"@type": TEST_TYPE}).pretty_print(), str)


def test_msg_type():
    assert MsgType.parse("doc/protocol/1.0/name") == MsgType.unparse(
        "doc/", "protocol", "1.0", "name"
    )


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
        "doc_uri/protocol/1.0.0.0.0.0/type",
    ],
)
def test_bad_message_type(type_str):
    """Test bad message types raise InvalidMessage"""
    with pytest.raises(InvalidType):
        MsgType(type_str)


@pytest.mark.parametrize("id_", [{"id": "12345"}, [1, 2, 3, 4, 5]])
def test_bad_message_id(id_):
    """Test message with bad message id"""
    with pytest.raises(ValueError):
        Message.parse_obj({"@type": TEST_TYPE, "@id": id_})


def test_message_getitem():
    msg = Message(**{"@id": "test", "@type": "doc/protocol/1.0/name"})
    assert msg["@id"] == "test" == msg.id
    assert msg["@type"] == "doc/protocol/1.0/name" == msg.type


@pytest.mark.parametrize(
    "in_str, expected",
    [
        ("1.0", "1.0.0"),
        ("1.0.0", "1.0.0"),
        ("1.0.0-build", "1.0.0-build"),
    ],
)
def test_msg_version(in_str, expected):
    assert str(MsgVersion.from_str(in_str)) == expected


def test_subclass():
    class MyMessage(BaseMessage):
        msg_type = MsgType.unparse(
            doc_uri="doc", protocol="protocol", version="1.0", name="name"
        )
        my_value: str

    msg = MyMessage(my_value="test")
    assert msg.type
    assert msg.my_value
    assert MyMessage(
        type=MsgType.unparse(
            doc_uri="doc", protocol="protocol", version="1.0", name="name"
        ),
        my_value="test",
    )

    with pytest.raises(ValueError):
        MyMessage(type="another/protocol/1.0/name", my_value="test")
