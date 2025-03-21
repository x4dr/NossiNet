import base64


def encode_id(unencoded):
    return base64.b32encode(unencoded.encode()).decode().rstrip("=")


def decode_id(encoded):
    if not encoded:
        encoded = ""
    padding = "=" * (8 - (len(encoded) % 8))
    return base64.b32decode(encoded + padding).decode()
