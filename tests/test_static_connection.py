""" Test StaticConnection. """

import pytest
from aries_staticagent import StaticConnection


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
    """ Test that bad inputs raise an error. """
    with pytest.raises(TypeError):
        StaticConnection(*args)
