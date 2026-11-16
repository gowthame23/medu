import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
import jwt

from app.core.config import settings

# Argon2id password hasher
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=19456,  # 19 MiB
    parallelism=1,
    hash_len=32,
    salt_len=16
)


def hash_password(password: str) -> str:
    """Hashes password using Argon2id."""
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against Argon2id hash."""
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of a raw token for safe storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_audit_email(email: str) -> str:
    """Computes an HMAC-SHA256 of the email, keyed by a value derived from SECRET_KEY (not raw key)."""
    import hmac
    derived_key = hashlib.sha256((settings.SECRET_KEY + ":audit_email_salt").encode("utf-8")).digest()
    return hmac.new(derived_key, email.lower().strip().encode("utf-8"), hashlib.sha256).hexdigest()


def generate_secure_token(length_bytes: int = 32) -> Tuple[str, str]:
    """Generates a random token and returns (raw_token, token_hash)."""
    raw_token = secrets.token_urlsafe(length_bytes)
    hashed = hash_token(raw_token)
    return raw_token, hashed


def create_access_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Creates a short-lived access JWT (15 mins)."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload: Dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and verifies an access JWT."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def hash_verification_target(target: str) -> str:
    """Computes an HMAC-SHA256 of normalized target (email or phone), keyed by SECRET_KEY derived key."""
    import hmac
    derived_key = hashlib.sha256((settings.SECRET_KEY + ":verification_target_salt").encode("utf-8")).digest()
    return hmac.new(derived_key, target.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def hash_verification_code(challenge_id: str, code: str) -> str:
    """Computes an HMAC-SHA256 of code + challenge_id, keyed by SECRET_KEY derived key."""
    import hmac
    derived_key = hashlib.sha256((settings.SECRET_KEY + ":verification_code_salt").encode("utf-8")).digest()
    message = f"{challenge_id}:{code.strip()}"
    return hmac.new(derived_key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_audit_phone(phone: str) -> str:
    """Computes an HMAC-SHA256 of normalized phone, keyed by SECRET_KEY derived key."""
    import hmac
    derived_key = hashlib.sha256((settings.SECRET_KEY + ":audit_phone_salt").encode("utf-8")).digest()
    return hmac.new(derived_key, phone.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def encrypt_outbox_payload(data: dict) -> dict:
    """Encrypts payload using AES-256-GCM with key derived from SECRET_KEY."""
    import base64
    import json
    import os
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = hashlib.sha256((settings.SECRET_KEY + ":outbox_payload_enc").encode("utf-8")).digest()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(data).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return {
        "encrypted_data": base64.b64encode(ciphertext).decode("utf-8"),
        "nonce": base64.b64encode(nonce).decode("utf-8")
    }


def decrypt_outbox_payload(payload: dict) -> dict:
    """Decrypts AES-256-GCM encrypted outbox payload."""
    import base64
    import json
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = hashlib.sha256((settings.SECRET_KEY + ":outbox_payload_enc").encode("utf-8")).digest()
    aesgcm = AESGCM(key)
    nonce = base64.b64decode(payload["nonce"])
    ciphertext = base64.b64decode(payload["encrypted_data"])
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))
