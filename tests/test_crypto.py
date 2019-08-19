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
