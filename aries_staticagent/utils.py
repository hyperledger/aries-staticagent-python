""" General utils """
import datetime


def timestamp():
    """ return a timestamp. """
    return datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc
    ).isoformat(' ')
