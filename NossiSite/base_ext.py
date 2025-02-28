import base64


def encode_id(unencoded):
    return base64.urlsafe_b64encode(unencoded.encode()).decode()


def decode_id(encoded):
    return base64.urlsafe_b64decode(encoded).decode()
