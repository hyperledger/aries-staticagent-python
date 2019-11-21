""" Test Pack and Unpack. """

import pytest

from aries_staticagent import StaticConnection, Message, crypto, utils
from aries_staticagent.mtc import (
    CONFIDENTIALITY, INTEGRITY, DESERIALIZE_OK, NONREPUDIATION,
    AUTHENTICATED_ORIGIN
)

# pylint: disable=redefined-outer-name
@pytest.fixture(scope='module')
def alice_keys():
    """Generate alice's keys."""
    yield StaticConnection.Keys(*crypto.create_keypair())


@pytest.fixture(scope='module')
def bob_keys():
    """Generate bob's keys."""
    yield StaticConnection.Keys(*crypto.create_keypair())


@pytest.fixture(scope='module')
def alice(alice_keys, bob_keys):
    """ Create Alice's StaticConnection. """
    yield StaticConnection(alice_keys, their_vk=bob_keys.verkey)


@pytest.fixture(scope='module')
def bob(bob_keys, alice_keys):
    """ Create Bob's StaticConnection. """
    yield StaticConnection(bob_keys, their_vk=alice_keys.verkey)


def test_pack_unpack_auth(alice, bob):
    """ Test the pack-unpack loop with authcrypt. """
    msg = Message({'@type': 'doc;protocol/1.0/name'})
    packed_msg = alice.pack(msg)
    assert isinstance(packed_msg, bytes)

    unpacked_msg = bob.unpack(packed_msg)
    assert isinstance(unpacked_msg, Message)
    assert hasattr(unpacked_msg, 'mtc')
    assert unpacked_msg.mtc.is_authcrypted()
    assert unpacked_msg.mtc.ad['sender_vk'] == alice.verkey_b58
    assert unpacked_msg.mtc.ad['recip_vk'] == bob.verkey_b58


def test_pack_unpack_anon(alice, bob):
    """ Test the pack-unpack loop with anoncrypt. """
    msg = {'@type': 'doc;protocol/1.0/name'}
    packed_msg = alice.pack(msg, anoncrypt=True)
    assert isinstance(packed_msg, bytes)

    unpacked_msg = bob.unpack(packed_msg)
    assert isinstance(unpacked_msg, Message)
    assert hasattr(unpacked_msg, 'mtc')
    assert unpacked_msg.mtc.is_anoncrypted()
    assert unpacked_msg.mtc.ad['sender_vk'] is None
    assert unpacked_msg.mtc.ad['recip_vk'] == bob.verkey_b58


def test_pack_unpack_plaintext(alice, bob):
    """Test pack/unpack in plaintext."""
    msg = {'@type': 'doc;protocol/1.0/name'}
    packed_msg = alice.pack(msg, plaintext=True)
    assert isinstance(packed_msg, bytes)

    unpacked_msg = bob.unpack(packed_msg)
    assert isinstance(unpacked_msg, Message)
    assert hasattr(unpacked_msg, 'mtc')
    assert unpacked_msg.mtc.is_plaintext()
    assert unpacked_msg.mtc.ad['sender_vk'] is None
    assert unpacked_msg.mtc.ad['recip_vk'] is None


def test_plaintext_and_anoncrypt_raises_error(alice):
    """Test specifying both plaintext and anoncrypt raises an error."""
    with pytest.raises(ValueError):
        alice.pack({'test': 'test'}, plaintext=True, anoncrypt=True)


def test_pack_unpack_with_routing_keys(alice, bob):
    """Test packing for a connection with routing keys."""
    route1 = StaticConnection(crypto.create_keypair())
    route2 = StaticConnection(crypto.create_keypair())
    alice.update(routing_keys=[route1.verkey, route2.verkey])
    packed_message = alice.pack({'@type': 'doc;protocol/1.0/name'})

    route2_msg = route2.unpack(packed_message)
    assert route2_msg.type == utils.FORWARD
    assert route2_msg['to'] == route1.verkey_b58
    assert route2_msg.mtc.is_anoncrypted()
    assert route2_msg.mtc.ad['sender_vk'] is None

    route1_msg = route1.unpack(route2_msg['msg'])
    assert route1_msg.type == utils.FORWARD
    assert route1_msg['to'] == bob.verkey_b58
    assert route1_msg.mtc.is_anoncrypted()
    assert route1_msg.mtc.ad['sender_vk'] is None

    bob_msg = bob.unpack(route1_msg['msg'])
    assert bob_msg.type == 'doc;protocol/1.0/name'
    assert bob_msg.mtc.is_authcrypted()
    assert bob_msg.mtc.ad['sender_vk'] == alice.verkey_b58
    assert bob_msg.mtc.ad['recip_vk'] == bob.verkey_b58


def test_bad_input(alice):
    """ Test that bad input raises an error in pack. """
    with pytest.raises(TypeError):
        alice.pack('blah')
