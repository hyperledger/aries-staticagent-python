""" Test StaticConnection. """

import hashlib
from collections import namedtuple
import pytest
from aries_staticagent import StaticConnection, crypto


ConnectionInfo = namedtuple('ConnectionInfo', 'vk, sk, vk_b58, sk_b58, did')


def generate_test_info(seed=None):
    """Generate connection information from seed."""
    test_vk, test_sk = crypto.create_keypair(seed)
    test_vk_b58 = crypto.bytes_to_b58(test_vk)
    test_sk_b58 = crypto.bytes_to_b58(test_sk)
    test_did = crypto.bytes_to_b58(test_vk[:16])
    return ConnectionInfo(test_vk, test_sk, test_vk_b58, test_sk_b58, test_did)


@pytest.fixture(scope='module')
def my_test_info():
    """Get my test info."""
    return generate_test_info(
        hashlib.sha256(
            b'aries_staticagent.test_static_connection.my_test_info'
        ).digest()
    )


@pytest.fixture(scope='module')
def their_test_info():
    """Get my test info."""
    return generate_test_info(
        hashlib.sha256(
            b'aries_staticagent.test_static_connection.their_test_info'
        ).digest()
    )


@pytest.mark.parametrize(
    'args',
    [
        (b'my_vk', b'my_sk', b'their_vk', b'bad_endpoint'),
        (10, b'my_sk', b'their_vk', 'endpoint'),
        (b'my_vk', 10, b'their_vk', 'endpoint'),
        (b'my_vk', b'my_sk', 10, 'endpoint'),
    ]
)
def test_bad_inputs(args):
    """Test that bad inputs raise an error."""
    with pytest.raises(TypeError):
        StaticConnection(*args)


def test_byte_inputs_without_their_info(my_test_info):
    """Test that valid byte inputs yield expected values."""
    conn = StaticConnection(my_test_info.vk, my_test_info.sk)
    assert conn.my_vk == my_test_info.vk
    assert conn.my_sk == my_test_info.sk
    assert conn.my_vk_b58 == my_test_info.vk_b58
    assert conn.did == my_test_info.did


def test_b58_inputs_without_their_info(my_test_info):
    """Test that valid b58 inputs yield expected values."""
    conn = StaticConnection(my_test_info.vk_b58, my_test_info.sk_b58)
    assert conn.my_vk == my_test_info.vk
    assert conn.my_sk == my_test_info.sk
    assert conn.my_vk_b58 == my_test_info.vk_b58
    assert conn.did == my_test_info.did


def test_byte_inputs_with_their_info(my_test_info, their_test_info):
    """Test that valid byte inputs yield expected values."""
    conn = StaticConnection(
        my_test_info.vk, my_test_info.sk, their_test_info.vk
    )
    assert conn.my_vk == my_test_info.vk
    assert conn.my_sk == my_test_info.sk
    assert conn.my_vk_b58 == my_test_info.vk_b58
    assert conn.did == my_test_info.did
    assert conn.their_vk == their_test_info.vk
    assert conn.their_vk_b58 == their_test_info.vk_b58


def test_b58_inputs_with_their_info(my_test_info, their_test_info):
    """Test that valid b58 inputs yield expected values."""
    conn = StaticConnection(
        my_test_info.vk_b58, my_test_info.sk_b58, their_test_info.vk_b58
    )
    assert conn.my_vk == my_test_info.vk
    assert conn.my_sk == my_test_info.sk
    assert conn.my_vk_b58 == my_test_info.vk_b58
    assert conn.did == my_test_info.did
    assert conn.their_vk == their_test_info.vk
    assert conn.their_vk_b58 == their_test_info.vk_b58
