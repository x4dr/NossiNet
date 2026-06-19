"""Base32 encoding/decoding utilities for NossiSite identifiers."""

import base64


def encode_id(unencoded: str) -> str:
    """Encode a string to a base32 string without padding.

    Args:
        unencoded: The string to encode.

    Returns:
        Base32-encoded string with padding stripped.

    """
    return base64.b32encode(unencoded.encode()).decode().rstrip("=")


def decode_id(encoded: str) -> str:
    """Decode a base32-encoded string back to the original string.

    Args:
        encoded: The base32-encoded string (padding optional).

    Returns:
        The decoded string, or empty string if input is empty.

    """
    if not encoded:
        return ""
    if len(encoded) % 8:
        encoded += "=" * (8 - (len(encoded) % 8))
    return base64.b32decode(encoded).decode()
