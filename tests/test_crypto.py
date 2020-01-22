""" Test crypto functions. """
import hashlib
from aries_staticagent import crypto


def test_create_keypair_from_seed():
    """ Test keypair creation creates sane values. """
    verkey, sigkey = crypto.create_keypair(
        hashlib.sha256(b'test-keypair-from-seed').digest()
    )
    assert isinstance(verkey, bytes)
    assert isinstance(sigkey, bytes)


def test_b64_to_bytes_urlsafe_padding():
    """Test b64 (urlsafe) decode accepts with and without padding."""
    b64decode = crypto.b64_to_bytes
    padded = 'dGVzdGluZyBkZWNvZGluZyB3aXRoIGFuZCB3aXRob3V0IHBhZGRpbmc='
    unpadded = 'dGVzdGluZyBkZWNvZGluZyB3aXRoIGFuZCB3aXRob3V0IHBhZGRpbmc'
    decoded = 'testing decoding with and without padding'

    assert b64decode(padded, urlsafe=True).decode('ascii') == decoded
    assert b64decode(unpadded, urlsafe=True).decode('ascii') == decoded
