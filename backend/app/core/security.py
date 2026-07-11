from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Instantiate PasswordHasher using standard/default parameters (which uses Argon2id)
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using Argon2id.
    """
    return ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its Argon2id hash.
    Returns True if it matches, False otherwise.
    """
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False
