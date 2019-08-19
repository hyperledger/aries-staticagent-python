""" Test utilities. """

import re
from aries_staticagent import utils

REGEX = r'^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9]) (2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$'

MATCH = re.compile(REGEX).match


def test_timestamp():
    """ Test that the timestamp looks right. """
    timestamp = utils.timestamp()
    assert MATCH(timestamp)
