""" Message Trust Context. See Aries RFC 0029: Message Trust Contexts.

    This file is inspired by the example implementation contained within
    that RFC.
"""
from enum import Flag, auto
from typing import Optional


class ContextsConflict(Exception):
    """Thrown when the passed contexts overlap"""


class Context(Flag):
    """Flags for MTC"""

    NONE = 0
    SIZE_OK = auto()
    DESERIALIZE_OK = auto()
    KEYS_OK = auto()
    VALUES_OK = auto()
    CONFIDENTIALITY = auto()
    INTEGRITY = auto()
    AUTHENTICATED_ORIGIN = auto()
    NONREPUDIATION = auto()
    PFS = auto()
    UNIQUENESS = auto()
    LIMITED_SCOPE = auto()


LABELS = {
    Context.SIZE_OK: "size_ok",
    Context.DESERIALIZE_OK: "deserialize_ok",
    Context.KEYS_OK: "keys_ok",
    Context.VALUES_OK: "values_ok",
    Context.CONFIDENTIALITY: "confidentiality",
    Context.INTEGRITY: "integrity",
    Context.AUTHENTICATED_ORIGIN: "authenticated_origin",
    Context.NONREPUDIATION: "nonrepudiation",
    Context.PFS: "pfs",
    Context.UNIQUENESS: "uniqueness",
    Context.LIMITED_SCOPE: "limited_scope",
}


# Context Shortcuts
NONE = Context.NONE
SIZE_OK = Context.SIZE_OK
DESERIALIZE_OK = Context.DESERIALIZE_OK
KEYS_OK = Context.KEYS_OK
VALUES_OK = Context.VALUES_OK
CONFIDENTIALITY = Context.CONFIDENTIALITY
INTEGRITY = Context.INTEGRITY
AUTHENTICATED_ORIGIN = Context.AUTHENTICATED_ORIGIN
NONREPUDIATION = Context.NONREPUDIATION
PFS = Context.PFS
UNIQUENESS = Context.UNIQUENESS
LIMITED_SCOPE = Context.LIMITED_SCOPE

# Typical MTCs
AUTHCRYPT_AFFIRMED = CONFIDENTIALITY | INTEGRITY | DESERIALIZE_OK | AUTHENTICATED_ORIGIN
AUTHCRYPT_DENIED = NONREPUDIATION

ANONCRYPT_AFFIRMED = CONFIDENTIALITY | INTEGRITY | DESERIALIZE_OK
ANONCRYPT_DENIED = NONREPUDIATION | AUTHENTICATED_ORIGIN

PLAINTEXT_AFFIRMED = DESERIALIZE_OK
PLAINTEXT_DENIED = CONFIDENTIALITY | INTEGRITY | AUTHENTICATED_ORIGIN
# | NONREPUDIATION ?


class AdditionalData:
    """
    Container for data relevant to Message Trust.
    """

    __slots__ = ("sender", "recipient")

    def __init__(self, sender: str = None, recipient: str = None):
        self.sender = sender
        self.recipient = recipient


class MessageTrustContext:
    """Message Trust Context

    Holds the contexts as well as data associated with message trust
    contexts such as the keys used to encrypt the message and allowing us
    to know that the origin is authenticated, etc.
    """

    __slots__ = "_affirmed", "_denied", "additional_data"

    def __init__(
        self,
        affirmed: Context = Context.NONE,
        denied: Context = Context.NONE,
        additional_data: AdditionalData = None,
    ):

        if affirmed & denied != Context.NONE:
            raise ContextsConflict()

        self._affirmed = affirmed
        self._denied = denied
        self.additional_data = additional_data if additional_data else AdditionalData()

    @property
    def sender(self):
        """Shortcut to sender."""
        return self.additional_data.sender

    @property
    def recipient(self):
        """Shortcut to recipient."""
        return self.additional_data.recipient

    @property
    def affirmed(self):
        """Access affirmed contexts"""
        return self._affirmed

    @property
    def denied(self):
        """Access denied contexts"""
        return self._denied

    def __getitem__(self, context: Context):
        if (self._affirmed & context) == context:
            return True
        if (self._denied & context) == context:
            return False
        return None

    def __setitem__(self, context: Context, value: Optional[bool]):
        if not isinstance(context, Context):
            raise TypeError("index must be of type Context")

        if value is None:
            # Set undefined
            self._affirmed &= ~context
        elif value is True:
            self._affirmed |= context
            self._denied &= ~context
        elif value is False:
            self._denied |= context
            self._affirmed &= ~context
        else:
            raise TypeError(
                "Value of type bool or None was expected, got {}".format(type(value))
            )

    def __str__(self):
        str_repr = "mtc:"
        plus = []
        minus = []
        for context, label in LABELS.items():
            if self[context] is True:
                plus.append("+{}".format(label))
            elif self[context] is False:
                minus.append("-{}".format(label))

        str_repr = " ".join([str_repr] + plus + minus)
        return str_repr

    # Convenience methods
    def set_authcrypted(self, sender: str, recipient: str):
        """Set MTC to match authcrypt."""
        self._affirmed = AUTHCRYPT_AFFIRMED
        self._denied = AUTHCRYPT_DENIED
        self.additional_data.sender = sender
        self.additional_data.recipient = recipient

    def set_anoncrypted(self, recipient: str):
        """Set MTC to match anoncrypt."""
        self._affirmed = ANONCRYPT_AFFIRMED
        self._denied = ANONCRYPT_DENIED
        self.additional_data.sender = None
        self.additional_data.recipient = recipient

    def set_plaintext(self):
        """Set MTC to match plaintext."""
        self._affirmed = PLAINTEXT_AFFIRMED
        self._denied = PLAINTEXT_DENIED
        self.additional_data.sender = None
        self.additional_data.recipient = None

    def is_authcrypted(self):
        """MTC matches expected authcrypt."""
        return self[AUTHCRYPT_AFFIRMED] is True and self[AUTHCRYPT_DENIED] is False

    def is_anoncrypted(self):
        """MTC matches expected anoncrypt."""
        return self[ANONCRYPT_AFFIRMED] is True and self[ANONCRYPT_DENIED] is False

    def is_plaintext(self):
        """MTC matches expected plaintext."""
        return self[PLAINTEXT_AFFIRMED] is True and self[PLAINTEXT_DENIED] is False
