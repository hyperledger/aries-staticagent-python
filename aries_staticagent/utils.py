""" General utils """
import datetime
import asyncio


def timestamp():
    """ return a timestamp. """
    return datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc
    ).isoformat(' ')


class AsyncClaimResource:
    """
    Claim and wait for an asynchronously populated resource.

    Similar to a Queue with size of one but keeps track of whether a single
    worker is waiting on the resource.
    """
    def __init__(self):
        self._event = asyncio.Event()
        self._claimed = False
        self._value = []

    def claim(self):
        """Lay claim to the next value."""
        self._claimed = True

    async def retrieve(self):
        """Retreive the claimed value."""
        if not self.claimed():
            raise RuntimeError(
                'The resource must be claimed before it can be retrieved.'
            )
        if not self._event.is_set():  # Not already available
            await self._event.wait()

        if not self._value:
            raise RuntimeError(
                'Managed resource was not populated'
                ' before condition was notified!'
            )

        self._event.clear()
        return self._value.pop()

    def claimed(self):
        """Check if the next pending value is already claimed."""
        return self._claimed

    def satisfy(self, value):
        """Satisfy the claim to the next value."""
        self._value.append(value)
        self._event.set()
