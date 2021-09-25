""" Test utilities. """

import pytest

from aries_staticagent import utils, Message
from aries_staticagent.mtc import (
    AUTHCRYPT_AFFIRMED,
    AUTHCRYPT_DENIED,
    ANONCRYPT_AFFIRMED,
    ANONCRYPT_DENIED,
)


@pytest.fixture
def message():
    yield Message.parse_obj(
        {"@type": "doc_uri/protocol/0.1/test", "@id": "12345", "content": "test"}
    )


def test_preprocess():
    """Test preprocessing decorator."""

    def preprocessor(msg):
        msg["preprocessed"] = True
        return msg

    @utils.preprocess(preprocessor)
    def test_handler(msg):
        return msg

    handled = test_handler({})
    assert handled["preprocessed"]


@pytest.mark.asyncio
async def test_preprocess_async_handler():
    """Test preprocessing decorator."""

    def preprocessor(msg):
        msg["preprocessed"] = True
        return msg

    @utils.preprocess(preprocessor)
    async def test_handler(msg):
        return msg

    handled = await test_handler({})
    assert handled["preprocessed"]


@pytest.mark.asyncio
async def test_preprocess_async_handler_and_preprocessor():
    """Test preprocessing decorator."""

    async def preprocessor(msg):
        msg["preprocessed"] = True
        return msg

    @utils.preprocess_async(preprocessor)
    async def test_handler(msg):
        return msg

    handled = await test_handler({})
    assert handled["preprocessed"]


def test_validate(message):
    """Test validation of message"""

    def validator(msg):
        assert msg.id == "12345"
        return msg

    @utils.validate(validator)
    def validate_test(msg):
        assert msg

    validate_test(message)


def test_validate_modify_msg():
    """Test validation can modify the message."""

    def validator(msg):
        msg["modified"] = True
        return msg

    @utils.validate(validator)
    def test_handler(msg):
        assert msg["modified"]

    test_handler({})


def test_validate_with_other_decorators():
    """Test validation of message"""

    def validator(msg):
        assert msg["@id"] == "12345"
        msg["validated"] = True
        return msg

    def fake_route():
        """Register route decorator."""

        def _fake_route_decorator(func):
            return func

        return _fake_route_decorator

    @utils.validate(validator)
    @fake_route()
    def validate_test(msg):
        return msg

    @fake_route()
    @utils.validate(validator)
    def validate_test2(msg):
        return msg

    handled = validate_test({"@id": "12345"})
    assert handled["validated"]
    handled = validate_test2({"@id": "12345"})
    assert handled["validated"]


def test_mtc_decorator(message):
    """Test the MTC decorator."""

    @utils.mtc(AUTHCRYPT_AFFIRMED, AUTHCRYPT_DENIED)
    def mtc_test(msg):
        assert msg

    message.mtc[AUTHCRYPT_AFFIRMED] = True
    message.mtc[AUTHCRYPT_DENIED] = False
    mtc_test(message)


def test_mtc_decorator_not_met(message):
    """Test the MTC decorator."""

    @utils.mtc(AUTHCRYPT_AFFIRMED)
    def mtc_test(msg):
        assert msg

    message.mtc[AUTHCRYPT_AFFIRMED] = True
    message.mtc[AUTHCRYPT_DENIED] = False
    with pytest.raises(utils.InsufficientMessageTrust):
        mtc_test(message)


def test_authcrypted_decorator(message):
    """Test the authcrypted decorator."""

    @utils.authcrypted
    def mtc_test(msg):
        assert msg

    message.mtc[AUTHCRYPT_AFFIRMED] = True
    message.mtc[AUTHCRYPT_DENIED] = False
    mtc_test(message)


def test_authcrypted_decorator_not_met(message):
    """Test the authcrypted decorator."""

    @utils.authcrypted
    def mtc_test(msg):
        assert msg

    message.mtc[AUTHCRYPT_AFFIRMED] = True
    with pytest.raises(utils.InsufficientMessageTrust):
        mtc_test(message)


def test_anoncrypted_decorator(message):
    """Test the anoncrypted decorator."""

    @utils.anoncrypted
    def mtc_test(msg):
        assert msg

    message.mtc[ANONCRYPT_AFFIRMED] = True
    message.mtc[ANONCRYPT_DENIED] = False
    mtc_test(message)


def test_anoncrypted_decorator_not_met(message):
    """Test the anoncrypted decorator."""

    @utils.anoncrypted
    def mtc_test(msg):
        assert msg

    message.mtc[ANONCRYPT_AFFIRMED] = True
    with pytest.raises(utils.InsufficientMessageTrust):
        mtc_test(message)
