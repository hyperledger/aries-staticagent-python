""" Test StaticConnection. """

import hashlib
from collections import namedtuple
import pytest
from aries_staticagent import StaticConnection, MessageDeliveryError, crypto


ConnectionInfo = namedtuple('ConnectionInfo', 'keys, keys_b58, did')


def generate_test_info(seed=None):
    """Generate connection information from seed."""
    test_keys = StaticConnection.Keys(*crypto.create_keypair(seed))
    test_keys_b58 = StaticConnection.Keys(
        crypto.bytes_to_b58(test_keys.verkey),
        crypto.bytes_to_b58(test_keys.sigkey)
    )
    test_did = crypto.bytes_to_b58(test_keys.verkey[:16])
    return ConnectionInfo(test_keys, test_keys_b58, test_did)


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
    conn = StaticConnection(my_test_info.keys)
    assert conn.verkey == my_test_info.keys.verkey
    assert conn.sigkey == my_test_info.keys.sigkey
    assert conn.verkey_b58 == my_test_info.keys_b58.verkey
    assert conn.did == my_test_info.did


def test_b58_inputs_without_their_info(my_test_info):
    """Test that valid b58 inputs yield expected values."""
    conn = StaticConnection(my_test_info.keys_b58)
    assert conn.verkey == my_test_info.keys.verkey
    assert conn.sigkey == my_test_info.keys.sigkey
    assert conn.verkey_b58 == my_test_info.keys_b58.verkey
    assert conn.did == my_test_info.did


def test_byte_inputs_with_their_info(my_test_info, their_test_info):
    """Test that valid byte inputs yield expected values."""
    conn = StaticConnection(
        my_test_info.keys,
        their_vk=their_test_info.keys.verkey,
        endpoint='endpoint'
    )
    assert conn.verkey == my_test_info.keys.verkey
    assert conn.sigkey == my_test_info.keys.sigkey
    assert conn.verkey_b58 == my_test_info.keys_b58.verkey
    assert conn.did == my_test_info.did
    assert conn.recipients == [their_test_info.keys.verkey]
    assert conn.endpoint == 'endpoint'


def test_b58_inputs_with_their_info(my_test_info, their_test_info):
    """Test that valid b58 inputs yield expected values."""
    conn = StaticConnection(
        my_test_info.keys_b58,
        their_vk=their_test_info.keys_b58.verkey
    )
    assert conn.verkey == my_test_info.keys.verkey
    assert conn.sigkey == my_test_info.keys.sigkey
    assert conn.verkey_b58 == my_test_info.keys_b58.verkey
    assert conn.did == my_test_info.did
    assert conn.recipients == [their_test_info.keys.verkey]


def test_their_vk_and_recipients_raises_error(my_test_info, their_test_info):
    """Test specifying both their_vk and recipients raises an error."""
    with pytest.raises(ValueError):
        StaticConnection(
            my_test_info.keys,
            their_vk=their_test_info.keys.verkey,
            recipients=[their_test_info.keys.verkey]
        )


def test_give_recipients(my_test_info, their_test_info):
    """Test recipients set when specified."""
    conn = StaticConnection(
        my_test_info.keys,
        recipients=[their_test_info.keys.verkey],
    )
    assert conn.recipients == [their_test_info.keys.verkey]


def test_give_recipients_b58(my_test_info, their_test_info):
    """Test recipients set when specified."""
    conn = StaticConnection(
        my_test_info.keys,
        recipients=[their_test_info.keys_b58.verkey],
    )
    assert conn.recipients == [their_test_info.keys.verkey]


def test_give_routing_keys(my_test_info, their_test_info):
    """Test routing_keys set when specified."""
    conn = StaticConnection(
        my_test_info.keys,
        their_vk=their_test_info.keys.verkey,
        routing_keys=[their_test_info.keys.verkey]
    )
    assert conn.recipients == [their_test_info.keys.verkey]
    assert conn.routing_keys == [their_test_info.keys.verkey]


def test_give_routing_keys_b58(my_test_info, their_test_info):
    """Test routing_keys set when specified."""
    conn = StaticConnection(
        my_test_info.keys,
        their_vk=their_test_info.keys.verkey,
        routing_keys=[their_test_info.keys_b58.verkey]
    )
    assert conn.recipients == [their_test_info.keys.verkey]
    assert conn.routing_keys == [their_test_info.keys.verkey]


def test_update(my_test_info, their_test_info):
    their_new_info = generate_test_info()
    conn = StaticConnection(
        my_test_info.keys,
        their_vk=their_test_info.keys.verkey,
        routing_keys=[their_test_info.keys.verkey],
        endpoint='endpoint1'
    )

    assert conn.verkey == my_test_info.keys.verkey
    assert conn.sigkey == my_test_info.keys.sigkey
    assert conn.verkey_b58 == my_test_info.keys_b58.verkey
    assert conn.did == my_test_info.did

    assert conn.recipients == [their_test_info.keys.verkey]
    assert conn.routing_keys == [their_test_info.keys.verkey]
    assert conn.endpoint == 'endpoint1'

    with pytest.raises(ValueError):
        conn.update(
            their_vk=their_new_info.keys.verkey,
            recipients=[their_new_info.keys.verkey]
        )

    conn.update(
        their_vk=their_new_info.keys.verkey,
        routing_keys=[their_new_info.keys.verkey],
        endpoint='endpoint2'
    )

    assert conn.recipients == [their_new_info.keys.verkey]
    assert conn.routing_keys == [their_new_info.keys.verkey]
    assert conn.endpoint == 'endpoint2'

    conn.update(
        their_vk=their_test_info.keys.verkey,
        routing_keys=[their_test_info.keys.verkey],
    )
    assert conn.recipients == [their_test_info.keys.verkey]
    assert conn.routing_keys == [their_test_info.keys.verkey]
    assert conn.endpoint == 'endpoint2'

    conn.update(
        recipients=[their_new_info.keys.verkey]
    )
    assert conn.recipients == [their_new_info.keys.verkey]

    conn.update(
        recipients=[their_test_info.keys_b58.verkey]
    )
    assert conn.recipients == [their_test_info.keys.verkey]


def test_message_delivery_error():
    """Test MessageDeliveryError."""
    error = MessageDeliveryError(status=10, msg='asdf')
    assert error.status == 10
    assert str(error) == 'asdf'
