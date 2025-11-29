import os
import json
import base64
import hashlib
import hmac
from typing import Tuple


def _hide_file_on_windows(file_path: str) -> None:
    """Hide a file on Windows by setting hidden and system attributes."""
    try:
        import ctypes
        FILE_ATTRIBUTE_HIDDEN = 0x02
        FILE_ATTRIBUTE_SYSTEM = 0x04
        ctypes.windll.kernel32.SetFileAttributesW(file_path, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
    except Exception:
        pass


def _hash_password(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)


def ensure_password_file(auth_path: str, default_password: str = "Admin") -> None:
    """Ensure an auth file exists; if not, create it with the default password."""
    if os.path.exists(auth_path):
        return

    salt = os.urandom(16)
    iterations = 200_000
    pwd_hash = _hash_password(default_password, salt, iterations)

    data = {
        'salt': base64.b64encode(salt).decode('ascii'),
        'hash': base64.b64encode(pwd_hash).decode('ascii'),
        'iterations': iterations
    }

    # Write atomically to avoid partial writes or permission race issues
    _atomic_write_json(auth_path, data)
    
    # Hide the auth file on Windows
    _hide_file_on_windows(auth_path)


def _load_auth(auth_path: str) -> Tuple[bytes, bytes, int]:
    with open(auth_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    salt = base64.b64decode(data['salt'])
    pwd_hash = base64.b64decode(data['hash'])
    iterations = int(data.get('iterations', 200_000))
    return salt, pwd_hash, iterations


def verify_password(auth_path: str, password: str) -> bool:
    """Verify a password against the stored auth file."""
    if not os.path.exists(auth_path):
        # No auth file: treat as failure (caller should create via ensure_password_file)
        return False

    try:
        salt, stored_hash, iterations = _load_auth(auth_path)
        candidate = _hash_password(password, salt, iterations)
        # Use hmac.compare_digest which is portable across Python versions
        try:
            return hmac.compare_digest(candidate, stored_hash)
        except Exception:
            # Fallback to simple equality (less secure against timing attacks)
            return candidate == stored_hash
    except Exception:
        return False


def set_password(auth_path: str, new_password: str) -> bool:
    """Set a new password, overwriting the auth file with a new salt and hash."""
    try:
        salt = os.urandom(16)
        iterations = 200_000
        pwd_hash = _hash_password(new_password, salt, iterations)

        data = {
            'salt': base64.b64encode(salt).decode('ascii'),
            'hash': base64.b64encode(pwd_hash).decode('ascii'),
            'iterations': iterations
        }

        _atomic_write_json(auth_path, data)
        
        # Hide the auth file on Windows
        _hide_file_on_windows(auth_path)
        
        return True
    except Exception:
        try:
            print(f"[auth] set_password failed for {auth_path}")
        except Exception:
            pass
        return False


def _atomic_write_json(path: str, data: dict) -> None:
    """Write JSON data atomically to `path`.

    Writes to a temporary file in the same directory and then replaces the target.
    Ensures data is flushed to disk before replace.
    """
    dirpath = os.path.dirname(path) or '.'
    tmp_path = os.path.join(dirpath, f".{os.path.basename(path)}.tmp")
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                # fsync may not be available on all platforms; ignore if it fails
                pass

        # On Windows, os.replace is atomic as of Python 3.3+
        os.replace(tmp_path, path)

        # Try to restrict permissions where possible
        try:
            # 0o600 -> owner read/write
            os.chmod(path, 0o600)
        except Exception:
            pass
    finally:
        # Clean up temp file if it still exists
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
