import os
import sys
import tempfile
try:
    from PyQt6.QtCore import QStandardPaths
except Exception:
    QStandardPaths = None

try:
    from cryptography.fernet import Fernet
except Exception:
    Fernet = None

# Legacy key support for backward compatibility with files encrypted before the security update
# If you have old encrypted files, create a legacy_key.key file with your old key
# Run setup_legacy_key.py to configure this if needed
def _load_legacy_key() -> bytes:
    """Load legacy key from file if it exists."""
    try:
        data_dir = _get_data_dir()
        legacy_key_path = os.path.join(data_dir, 'legacy_key.key')
        if os.path.exists(legacy_key_path):
            with open(legacy_key_path, 'rb') as f:
                return f.read()
    except Exception:
        pass
    return None


def _get_data_dir(app_name: str = "DatabasePro") -> str:
    """Return the data directory (parent of files dir) for storing keys and config."""
    # Usa LocalAppData per evitare problemi di permessi
    # ProgramData richiede privilegi admin per scrivere file
    try:
        local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        path = os.path.join(local_app_data, app_name)
        os.makedirs(path, exist_ok=True)
        return path
    except Exception:
        pass
    
    # Fallback: directory home dell'utente
    try:
        home = os.path.expanduser('~')
        path = os.path.join(home, f'.{app_name}')
        os.makedirs(path, exist_ok=True)
        return path
    except Exception:
        # fallback finale: current working directory
        return os.getcwd()


def _load_or_create_files_key(key_path: str) -> bytes:
    """Load or create the encryption key for file attachments.
    
    Similar to database key management: creates a unique key per installation.
    """
    try:
        if os.path.exists(key_path):
            with open(key_path, 'rb') as kf:
                return kf.read()
        else:
            if Fernet is None:
                raise RuntimeError('cryptography not installed')
            key = Fernet.generate_key()
            # Write with restricted permissions where possible
            with open(key_path, 'wb') as kf:
                kf.write(key)
            try:
                # chmod 600 on Unix; best-effort on Windows
                os.chmod(key_path, 0o600)
            except Exception:
                pass
            
            # Hide the key file for additional security on Windows
            try:
                import ctypes
                FILE_ATTRIBUTE_HIDDEN = 0x02
                FILE_ATTRIBUTE_SYSTEM = 0x04
                ctypes.windll.kernel32.SetFileAttributesW(key_path, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
            except Exception:
                pass
            
            return key
    except Exception:
        return None


def get_files_dir(app_name: str = "DatabasePro") -> str:
    """Return a writable directory to store app files (attachments).

    Ensures the directory exists and returns its path.
    """
    try:
        data_dir = _get_data_dir(app_name)
        files_dir = os.path.join(data_dir, 'files')
        os.makedirs(files_dir, exist_ok=True)
        return files_dir
    except Exception:
        # final fallback: current working directory/files
        files_dir = os.path.join(os.getcwd(), 'files')
        try:
            os.makedirs(files_dir, exist_ok=True)
        except Exception:
            pass
        return files_dir


def get_file_fernet(app_name: str = "DatabasePro"):
    """Return a Fernet instance for file encryption.
    
    Uses a unique key stored in files_key.key (created automatically if missing).
    This provides better security than a hardcoded key embedded in the executable.
    """
    if Fernet is None:
        return None
    
    try:
        data_dir = _get_data_dir(app_name)
        key_path = os.path.join(data_dir, 'files_key.key')
        key = _load_or_create_files_key(key_path)
        
        if key is None:
            return None
        
        return Fernet(key)
    except Exception:
        return None


def delete_encrypted_file(encrypted_filename: str) -> bool:
    """Delete an encrypted file from the files directory.
    
    Returns True if deleted successfully, False otherwise.
    """
    if not encrypted_filename:
        return False
    
    try:
        files_dir = get_files_dir()
        file_path = os.path.join(files_dir, encrypted_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False


def encrypt_file(src_path: str, dest_path: str) -> bool:
    """Encrypt a file and save to dest_path.
    
    Returns True on success, False on failure.
    """
    try:
        fernet = get_file_fernet()
        if fernet is None:
            # No encryption available, just copy
            import shutil
            shutil.copy2(src_path, dest_path)
            return True
        
        with open(src_path, 'rb') as f:
            data = f.read()
        
        encrypted = fernet.encrypt(data)
        
        with open(dest_path, 'wb') as f:
            f.write(encrypted)
        
        return True
    except Exception:
        return False


def decrypt_file_to_temp(encrypted_filename: str, original_name: str) -> str:
    """Decrypt a file and return the path to a temporary file.
    
    The caller is responsible for deleting the temp file after use.
    Returns the temp file path, or None on failure.
    
    Handles migration from legacy hardcoded key to new unique key automatically.
    """
    try:
        files_dir = get_files_dir()
        encrypted_path = os.path.join(files_dir, encrypted_filename)
        
        if not os.path.exists(encrypted_path):
            return None
        
        fernet = get_file_fernet()
        
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        
        decrypted_data = None
        needs_migration = False
        
        if fernet is not None:
            try:
                # Try decrypting with current key
                decrypted_data = fernet.decrypt(encrypted_data)
            except Exception:
                # Try with legacy key for backward compatibility
                legacy_key = _load_legacy_key()
                if legacy_key and Fernet is not None:
                    try:
                        legacy_fernet = Fernet(legacy_key)
                        decrypted_data = legacy_fernet.decrypt(encrypted_data)
                        needs_migration = True  # Mark for re-encryption
                    except Exception:
                        # File might not be encrypted at all (very old legacy file)
                        decrypted_data = encrypted_data
                else:
                    # No legacy key available, file might not be encrypted
                    decrypted_data = encrypted_data
        else:
            decrypted_data = encrypted_data
        
        # If file was decrypted with legacy key, re-encrypt with new key
        if needs_migration and fernet is not None:
            try:
                with open(encrypted_path, 'wb') as f:
                    f.write(fernet.encrypt(decrypted_data))
            except Exception:
                pass  # Migration failed, but file is still readable
        
        # Create temp file with original extension
        ext = os.path.splitext(original_name)[1]
        fd, temp_path = tempfile.mkstemp(suffix=ext)
        
        with os.fdopen(fd, 'wb') as f:
            f.write(decrypted_data)
        
        return temp_path
    except Exception:
        return None


def parse_file_value(db_value: str) -> tuple:
    """Parse a file value from DB into (original_name, encrypted_filename).
    
    Format in DB: "original_name|encrypted_filename"
    For legacy files without separator, returns (db_value, db_value)
    """
    if not db_value:
        return (None, None)
    
    if '|' in db_value:
        parts = db_value.split('|', 1)
        return (parts[0], parts[1])
    else:
        # Legacy format: filename only
        return (db_value, db_value)


def format_file_value(original_name: str, encrypted_filename: str) -> str:
    """Format file value for DB storage.
    
    Returns: "original_name|encrypted_filename"
    """
    return f"{original_name}|{encrypted_filename}"


def parse_multi_file_value(db_value: str) -> list:
    """Parse a multi-file value from DB into list of (original_name, encrypted_filename) tuples.
    
    Format in DB: "original1|encrypted1;;original2|encrypted2;;..."
    Also handles single file format for backwards compatibility.
    """
    if not db_value:
        return []
    
    files = []
    # Split by ";;" for multiple files
    parts = db_value.split(';;')
    for part in parts:
        if part.strip():
            original, encrypted = parse_file_value(part.strip())
            if original and encrypted:
                files.append((original, encrypted))
    
    return files


def format_multi_file_value(files: list) -> str:
    """Format multiple files for DB storage.
    
    files: list of (original_name, encrypted_filename) tuples
    Returns: "original1|encrypted1;;original2|encrypted2;;..."
    """
    if not files:
        return ""
    
    parts = [format_file_value(orig, enc) for orig, enc in files]
    return ";;".join(parts)


def get_display_names_from_multi_file(db_value: str) -> str:
    """Get comma-separated display names from multi-file DB value."""
    files = parse_multi_file_value(db_value)
    if not files:
        return ""
    return ", ".join([f[0] for f in files])
