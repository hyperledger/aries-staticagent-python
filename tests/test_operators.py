import pytest

from aries_staticagent import Message
from aries_staticagent.operators import (
    all,
    any,
    in_protocol,
    is_reply_to,
    msg_type_is,
    msg_type_is_compatible_with,
    msg_type_matches,
)


@pytest.fixture
def message():
    yield Message.parse_obj({"@type": "doc;protocol/1.0/name"})


def test_all():
    assert all([lambda f: True, lambda f: True, lambda f: True], "value")
    assert all([lambda f: True, lambda f: True, lambda f: False], "value") is False


def test_any():
    assert any([lambda f: True, lambda f: True, lambda f: True], "value")
    assert any([lambda f: True, lambda f: True, lambda f: False], "value")
    assert any([lambda f: True, lambda f: False, lambda f: False], "value")
    assert any([lambda f: False, lambda f: False, lambda f: False], "value") is False


def test_msg_type_is(message):
    assert msg_type_is(message.type, message)


def test_msg_type_matches(message):
    assert msg_type_matches(r"^.*protocol/1.0.*$", message)


def test_msg_type_is_compatibile_with(message):
    assert msg_type_is_compatible_with("doc;protocol/1.1/name", message)


def test_in_protocol(message):
    assert in_protocol("doc;protocol/1.0", message)


def test_is_reply_to():
    original = Message.parse_obj({"@type": "doc;protocol/1.0/name"})
    message = Message.parse_obj(
        {"@type": "doc;protocol/1.0/name", "~thread": {"thid": original.id}}
    )
    assert is_reply_to(original, message)
