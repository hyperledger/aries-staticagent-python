""" Test Pack and Unpack. """

import pytest

from aries_staticagent import StaticConnection, Message, crypto
from aries_staticagent.mtc import (
    CONFIDENTIALITY, INTEGRITY, DESERIALIZE_OK, NONREPUDIATION,
    AUTHENTICATED_ORIGIN
)

# pylint: disable=redefined-outer-name
@pytest.fixture
def keys():
    """ Generate keys for testing. """
    alice_vk, alice_sk = crypto.create_keypair()
    bob_vk, bob_sk = crypto.create_keypair()
    return alice_vk, alice_sk, bob_vk, bob_sk


@pytest.fixture
def alice(keys):
    """ Create Alice's StaticConnection. """
    alice_vk, alice_sk, bob_vk, _bob_sk = keys
    yield StaticConnection((alice_vk, alice_sk), their_vk=bob_vk, endpoint='')


@pytest.fixture
def bob(keys):
    """ Create Bob's StaticConnection. """
    alice_vk, _alice_sk, bob_vk, bob_sk = keys
    yield StaticConnection((bob_vk, bob_sk), their_vk=alice_vk, endpoint='')


def test_pack_unpack_auth(keys, alice, bob):
    """ Test the pack-unpack loop with authcrypt. """
    alice_vk, _alice_sk, bob_vk, _bob_sk = keys
    msg = Message({'@type': 'doc;protocol/1.0/name'})
    packed_msg = alice.pack(msg)
    assert isinstance(packed_msg, bytes)

    unpacked_msg = bob.unpack(packed_msg)
    assert isinstance(unpacked_msg, Message)
    assert hasattr(unpacked_msg, 'mtc')
    assert unpacked_msg.mtc[
        CONFIDENTIALITY | INTEGRITY | DESERIALIZE_OK | AUTHENTICATED_ORIGIN
    ]
    assert unpacked_msg.mtc[NONREPUDIATION] is False
    assert unpacked_msg.mtc.ad['sender_vk'] == crypto.bytes_to_b58(alice_vk)
    assert unpacked_msg.mtc.ad['recip_vk'] == crypto.bytes_to_b58(bob_vk)


def test_pack_unpack_anon(keys, alice, bob):
    """ Test the pack-unpack loop with anoncrypt. """
    _alice_vk, _alice_sk, bob_vk, _bob_sk = keys
    msg = {'@type': 'doc;protocol/1.0/name'}
    packed_msg = alice.pack(msg, anoncrypt=True)
    assert isinstance(packed_msg, bytes)

    unpacked_msg = bob.unpack(packed_msg)
    assert isinstance(unpacked_msg, Message)
    assert hasattr(unpacked_msg, 'mtc')
    assert unpacked_msg.mtc[
        CONFIDENTIALITY | INTEGRITY | DESERIALIZE_OK
    ]
    assert unpacked_msg.mtc[NONREPUDIATION | AUTHENTICATED_ORIGIN] is False
    assert unpacked_msg.mtc.ad['sender_vk'] is None
    assert unpacked_msg.mtc.ad['recip_vk'] == crypto.bytes_to_b58(bob_vk)


def test_bad_input(alice):
    """ Test that bad input raises an error in pack. """
    with pytest.raises(TypeError):
        alice.pack('blah')
