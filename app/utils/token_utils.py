import secrets
import uuid
import base64
import hashlib

def generate_auth_key() -> str:
    """Generate a 64-character hex string for auth_key"""
    return secrets.token_hex(32)

def generate_uuid() -> str:
    """Generate a UUID string"""
    return str(uuid.uuid4())

def get_cookie_suffixes():
    """Generate all required cookie suffixes"""
    return {
        'device_id': generate_suffix(43),  # Length of BrFYlS5k1zCjWf0DYFyJFmnovYZoqdylYbymDFk2xGM
        'tid': generate_suffix(43),        # Length of NU5BAUVdu%2Bmi0zeGabam6243GToqLIZd2N%2FapZLRqqI
        'sid': generate_suffix(43)         # Length of u1k9SnwOGqjwwSCOY3WOJ3OcsoYInH8uzSLh34bX0AE
    }

def generate_suffix(length: int) -> str:
    """Generate a base64 suffix of specified length"""
    random_bytes = secrets.token_bytes(length)
    base64_str = base64.b64encode(random_bytes).decode('utf-8')
    return base64_str.rstrip('=')[:length]

def generate_matcher_id() -> str:
    """Generate a matcher ID (20-character hex string)"""
    return secrets.token_hex(10)

def generate_xsrf_token() -> str:
    """Generate XSRF token with specific format"""
    part1 = generate_suffix(22)
    part2 = generate_suffix(32)
    part3 = generate_suffix(43)
    return f"{part1}:{part2}.{part3}"

def generate_request_signature(http_method: str, url_path: str, body: str, request_id: str, device_id: str, xsrf_secret: str) -> str:
    signature_dict = {
        "body": body,
        "deviceId": device_id,
        "method": http_method.lower(),
        "requestId": request_id,
        "secret": xsrf_secret,
        "url": url_path
    }

    sorted_keys = sorted(signature_dict.keys())
    to_hash = "|".join([signature_dict[key] for key in sorted_keys])

    sha256 = hashlib.sha256()
    sha256.update(to_hash.encode('utf-8'))
    return sha256.hexdigest()


