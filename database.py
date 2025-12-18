import sqlite3
import csv
import shutil
import tempfile
import os
from typing import Optional, Dict, List, Tuple
from collections import deque

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:
    Fernet = None
    InvalidToken = Exception


def _clear_file_attributes(file_path: str) -> bool:
    """Remove hidden/system attributes from a file on Windows to allow overwriting."""
    try:
        import ctypes
        from ctypes import wintypes
        
        # Define the function properly
        kernel32 = ctypes.windll.kernel32
        SetFileAttributesW = kernel32.SetFileAttributesW
        SetFileAttributesW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
        SetFileAttributesW.restype = wintypes.BOOL
        
        FILE_ATTRIBUTE_NORMAL = 0x80
        result = SetFileAttributesW(file_path, FILE_ATTRIBUTE_NORMAL)
        return bool(result)
    except Exception:
        # Fallback: try using os.chmod
        try:
            import stat
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            return True
        except Exception:
            pass
    return False


def _set_hidden_system_attributes(file_path: str) -> bool:
    """Set hidden attribute on a file on Windows (without System to avoid permission issues)."""
    try:
        import ctypes
        from ctypes import wintypes
        
        kernel32 = ctypes.windll.kernel32
        SetFileAttributesW = kernel32.SetFileAttributesW
        SetFileAttributesW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
        SetFileAttributesW.restype = wintypes.BOOL
        
        # Solo HIDDEN, non SYSTEM - altrimenti non possiamo sovrascrivere senza admin
        FILE_ATTRIBUTE_HIDDEN = 0x02
        result = SetFileAttributesW(file_path, FILE_ATTRIBUTE_HIDDEN)
        return bool(result)
    except Exception:
        pass
    return False


class DatabaseManager:
    def __init__(self, db_path: str, key: bytes = None, key_path: Optional[str] = None):
        """
        db_path: path to base db file (will be stored as <db_path>.enc when encrypted)
        key: raw Fernet key (optional). If not provided and key_path given, key is loaded from file.
        key_path: if provided and key missing, will attempt to read key from this path. If not exists, a key is generated and saved.
        
        Runs the DB against a temporary decrypted copy when encryption is enabled.
        """
        self.db_path = db_path
        self.encrypted_path = f"{db_path}.enc"
        self._temp_db_file = None
        self._uses_encryption = False
        self._fernet = None

        # Load or generate key if requested
        if key is None and key_path:
            key = self._load_or_create_key_file(key_path)

        if key and Fernet is not None:
            self._uses_encryption = True
            self._fernet = Fernet(key)
            # Ensure encrypted storage exists; if only plain DB exists, migrate it
            if os.path.exists(self.encrypted_path):
                # decrypt to temp and use
                self._temp_db_file = self._decrypt_to_temp(self.encrypted_path)
            else:
                if os.path.exists(self.db_path):
                    # encrypt existing plain DB to encrypted_path, then decrypt to temp
                    self._encrypt_file(self.db_path, self.encrypted_path)
                    # remove plain file to avoid leaving unencrypted copy
                    try:
                        os.remove(self.db_path)
                    except Exception:
                        pass
                    self._temp_db_file = self._decrypt_to_temp(self.encrypted_path)
                else:
                    # no db exists yet; create an empty temp DB
                    self._temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db').name
        else:
            # no encryption: work directly on db_path
            self._temp_db_file = self.db_path

        # Connect to the working DB (either temp decrypted file or plain path)
        self.conn = sqlite3.connect(self._temp_db_file)
        self.cursor = self.conn.cursor()
        self._init_metadata()

        # Sistema di undo/redo (max 3 operazioni)
        self.undo_stack = deque(maxlen=3)
        self.redo_stack = deque(maxlen=3)
        
        # Contatore per sync periodico
        self._operation_count = 0
        self._sync_interval = 1  # Sync ad ogni operazione per massima sicurezza
    
    def _init_metadata(self):
        sql = """
        CREATE TABLE IF NOT EXISTS _sys_columns (
            table_name TEXT,
            col_name TEXT,
            special_type TEXT,
            extra_info TEXT,
            PRIMARY KEY (table_name, col_name)
        )
        """
        self.cursor.execute(sql)
        self.conn.commit()

    def sync(self):
        """Sincronizza il database: commit e crittografa il file temporaneo.
        
        Chiamare periodicamente per evitare perdita dati in caso di crash.
        """
        try:
            if getattr(self, 'conn', None):
                self.conn.commit()
                # Force WAL checkpoint - use TRUNCATE for more aggressive write
                try:
                    self.cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except Exception:
                    pass
            
            if self._uses_encryption and self._temp_db_file and os.path.exists(self._temp_db_file):
                # Rimuovi attributi nascosti/sistema per poter sovrascrivere
                if os.path.exists(self.encrypted_path):
                    _clear_file_attributes(self.encrypted_path)
                
                # Verifica che il file temp esista e non sia vuoto
                temp_size = os.path.getsize(self._temp_db_file)
                if temp_size > 0:
                    self._encrypt_file(self._temp_db_file, self.encrypted_path)
                    # Nascondi il file crittografato
                    _set_hidden_system_attributes(self.encrypted_path)
        except Exception as e:
            print(f"Error during sync: {e}")
    
    def _maybe_sync(self):
        """Sync automatico dopo un certo numero di operazioni."""
        self._operation_count += 1
        if self._operation_count >= self._sync_interval:
            self._operation_count = 0
            self.sync()

    # --- Encryption helpers ---
    def _load_or_create_key_file(self, key_path: str) -> bytes:
        """Carica la chiave da `key_path` o ne crea una nuova con permessi ristretti."""
        try:
            if os.path.exists(key_path):
                with open(key_path, 'rb') as kf:
                    return kf.read()
            else:
                if Fernet is None:
                    raise RuntimeError('cryptography not installed')
                key = Fernet.generate_key()
                # Scrivi il file con permessi ristretti ove possibile
                with open(key_path, 'wb') as kf:
                    kf.write(key)
                try:
                    # chmod 600 on Unix; on Windows this is best-effort
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

    def _decrypt_to_temp(self, source_path: str) -> str:
        """Decrypt `source_path` (encrypted) to a temp file and return its path."""
        if self._fernet is None:
            raise RuntimeError('Encryption not configured')
        with open(source_path, 'rb') as ef:
            encrypted = ef.read()
        try:
            decrypted = self._fernet.decrypt(encrypted)
        except InvalidToken:
            raise
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        tmp_path = tmp.name
        tmp.close()
        with open(tmp_path, 'wb') as tf:
            tf.write(decrypted)
        return tmp_path

    def _encrypt_file(self, source_path: str, dest_path: str):
        """Encrypt source_path into dest_path using the current Fernet key."""
        if self._fernet is None:
            raise RuntimeError('Encryption not configured')
        with open(source_path, 'rb') as sf:
            data = sf.read()
        token = self._fernet.encrypt(data)
        with open(dest_path, 'wb') as df:
            df.write(token)
        
        # Hide the encrypted database file for security on Windows
        try:
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            FILE_ATTRIBUTE_SYSTEM = 0x04
            ctypes.windll.kernel32.SetFileAttributesW(dest_path, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
        except Exception:
            pass
        
        # Also try chmod on Unix-like systems
        try:
            os.chmod(dest_path, 0o600)
        except Exception:
            pass
    
    def get_tables(self) -> List[str]:
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_sys_%'"
        )
        return [row[0] for row in self.cursor.fetchall()]
    
    def create_table(self, table_name: str, columns: List[Dict]) -> bool:
        try:
            cols_sql = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for col in columns:
                cols_sql.append(f'"{col["name"]}" {col["sql_type"]}')
            
            cols_joined = ", ".join(cols_sql)
            sql = f'CREATE TABLE "{table_name}" ({cols_joined})'
            self.cursor.execute(sql)
            
            for col in columns:
                if col.get('special'):
                    self.save_special_type(
                        table_name, col['name'], 
                        col['special'], col.get('extra', '')
                    )
            
            self.conn.commit()
            self.sync()
            return True
        except Exception as e:
            print(f"Error creating table: {e}")
            return False
    
    def drop_table(self, table_name: str) -> bool:
        try:
            self.cursor.execute(f'DROP TABLE "{table_name}"')
            self.cursor.execute("DELETE FROM _sys_columns WHERE table_name=?", (table_name,))
            self.conn.commit()
            self.sync()
            return True
        except Exception:
            return False
    
    def get_columns(self, table_name: str) -> List[Tuple]:
        self.cursor.execute(f'PRAGMA table_info("{table_name}")')
        return self.cursor.fetchall()
    
    def get_records(self, table_name: str, where_clause: str = "", params: Tuple = ()) -> List[Tuple]:
        if where_clause:
            sql = f'SELECT * FROM "{table_name}" WHERE {where_clause}'
            self.cursor.execute(sql, params)
        else:
            self.cursor.execute(f'SELECT * FROM "{table_name}"')
        return self.cursor.fetchall()
    
    def insert_record(self, table_name: str, data: Dict) -> bool:
        try:
            cols = list(data.keys())
            quoted_cols = [f'"{c}"' for c in cols]
            placeholders = ", ".join(["?" for _ in cols])
            sql = f'INSERT INTO "{table_name}" ({", ".join(quoted_cols)}) VALUES ({placeholders})'
            self.cursor.execute(sql, list(data.values()))
            new_id = self.cursor.lastrowid
            self.conn.commit()
            
            # Salva per undo
            self.undo_stack.append({
                'action': 'insert',
                'table': table_name,
                'id': new_id
            })
            self.redo_stack.clear()
            
            # Sync periodico per evitare perdita dati
            self._maybe_sync()
            
            return True
        except Exception as e:
            print(f"Error inserting record: {e}")
            return False
    
    def update_record(self, table_name: str, record_id: int, data: Dict) -> bool:
        try:
            # Salva lo stato precedente per undo
            old_record = self.get_records(table_name, "id=?", (record_id,))
            
            cols = list(data.keys())
            set_clause = ", ".join([f'"{col}"=?' for col in cols])
            values = list(data.values()) + [record_id]
            sql = f'UPDATE "{table_name}" SET {set_clause} WHERE id=?'
            self.cursor.execute(sql, values)
            
            # Ottieni il nuovo record dopo l'update
            new_record = self.get_records(table_name, "id=?", (record_id,))
            
            self.conn.commit()
            
            # Salva per undo con sia old che new data
            if old_record and new_record:
                self.undo_stack.append({
                    'action': 'update',
                    'table': table_name,
                    'id': record_id,
                    'old_data': old_record[0],
                    'new_data': new_record[0]
                })
                self.redo_stack.clear()
            
            # Sync periodico per evitare perdita dati
            self._maybe_sync()
            
            return True
        except Exception as e:
            print(f"Error updating record: {e}")
            return False
    
    def delete_record(self, table_name: str, record_id: int) -> bool:
        try:
            # Salva il record per undo
            old_record = self.get_records(table_name, "id=?", (record_id,))
            
            self.cursor.execute(f'DELETE FROM "{table_name}" WHERE id=?', (record_id,))
            self.conn.commit()
            
            # Salva per undo
            if old_record:
                columns = self.get_columns(table_name)
                self.undo_stack.append({
                    'action': 'delete',
                    'table': table_name,
                    'id': record_id,
                    'old_data': old_record[0],
                    'columns': columns
                })
                self.redo_stack.clear()
            
            # Sync periodico per evitare perdita dati
            self._maybe_sync()
            
            return True
        except Exception:
            return False
    
    def add_column(self, table_name: str, col_name: str, sql_type: str, 
                  special_type: str = "", extra_info: str = "") -> bool:
        try:
            self.cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {sql_type}')
            if special_type:
                self.save_special_type(table_name, col_name, special_type, extra_info)
            self.conn.commit()
            self.sync()
            return True
        except Exception:
            return False
    
    def rename_column(self, table_name: str, old_name: str, new_name: str) -> bool:
        """Rinomina una colonna in una tabella"""
        try:
            # SQLite supporta ALTER TABLE RENAME COLUMN da versione 3.25+
            self.cursor.execute(f'ALTER TABLE "{table_name}" RENAME COLUMN "{old_name}" TO "{new_name}"')
            
            # Aggiorna anche i metadati se esistono
            self.cursor.execute(
                "UPDATE _sys_columns SET col_name=? WHERE table_name=? AND col_name=?",
                (new_name, table_name, old_name)
            )
            
            self.conn.commit()
            self.sync()
            return True
        except Exception as e:
            print(f"Error renaming column: {e}")
            return False
    
    def get_special_type(self, table_name: str, col_name: str) -> Optional[Tuple]:
        self.cursor.execute(
            "SELECT special_type, extra_info FROM _sys_columns WHERE table_name=? AND col_name=?",
            (table_name, col_name)
        )
        return self.cursor.fetchone()
    
    def save_special_type(self, table_name: str, col_name: str, special_type: str, extra_info: str = ""):
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO _sys_columns VALUES (?, ?, ?, ?)",
                (table_name, col_name, special_type, extra_info)
            )
            self.conn.commit()
        except Exception:
            pass
    
    def export_csv(self, table_name: str, file_path: str) -> bool:
        try:
            records = self.get_records(table_name)
            columns = [col[1] for col in self.get_columns(table_name)]
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in records:
                    clean_row = []
                    for cell in row:
                        if isinstance(cell, bytes):
                            clean_row.append("<BINARY_FILE>")
                        else:
                            clean_row.append(cell if cell is not None else "")
                    writer.writerow(clean_row)
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    def import_csv(self, table_name: str, file_path: str) -> Tuple[bool, int]:
        try:
            existing_cols = [col[1] for col in self.get_columns(table_name)]
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                
                missing = [h for h in headers if h not in existing_cols]
                if missing:
                    return False, 0
                
                quoted_headers = [f'"{h}"' for h in headers]
                placeholders = ", ".join(["?" for _ in headers])
                sql = f'INSERT INTO "{table_name}" ({", ".join(quoted_headers)}) VALUES ({placeholders})'
                
                count = 0
                for row in reader:
                    self.cursor.execute(sql, row)
                    count += 1
                
                self.conn.commit()
                self.sync()
                return True, count
        except Exception as e:
            print(f"Import error: {e}")
            return False, 0
    
    def backup_db(self, backup_path: str) -> bool:
        try:
            # If using encryption, back up the encrypted file; otherwise back up plain DB
            if self._uses_encryption and os.path.exists(self.encrypted_path):
                shutil.copy(self.encrypted_path, backup_path)
            else:
                shutil.copy(self.db_path, backup_path)
            return True
        except Exception:
            return False
    
    def can_undo(self) -> bool:
        """Verifica se ci sono operazioni da annullare"""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Verifica se ci sono operazioni da ripristinare"""
        return len(self.redo_stack) > 0
    
    def undo(self) -> Tuple[bool, str]:
        """Annulla l'ultima operazione"""
        if not self.can_undo():
            return False, "Nessuna operazione da annullare"
        
        try:
            operation = self.undo_stack.pop()
            action = operation['action']
            table = operation['table']
            
            if action == 'insert':
                # Annulla insert = delete
                record_id = operation['id']
                self.cursor.execute(f'DELETE FROM "{table}" WHERE id=?', (record_id,))
                self.redo_stack.append(operation)
                
            elif action == 'delete':
                # Annulla delete = re-insert
                old_data = operation['old_data']
                columns = operation['columns']
                col_names = [col[1] for col in columns]
                
                quoted_cols = [f'"{c}"' for c in col_names]
                placeholders = ", ".join(["?" for _ in col_names])
                sql = f'INSERT INTO "{table}" ({", ".join(quoted_cols)}) VALUES ({placeholders})'
                self.cursor.execute(sql, old_data)
                self.redo_stack.append(operation)
                
            elif action == 'update':
                # Annulla update = ripristina valori vecchi
                record_id = operation['id']
                old_data = operation['old_data']
                columns = self.get_columns(table)
                
                # Crea update con i vecchi valori
                col_names = [col[1] for col in columns[1:]]  # Skip ID
                set_clause = ", ".join([f'"{col}"=?' for col in col_names])
                values = list(old_data[1:]) + [record_id]
                sql = f'UPDATE "{table}" SET {set_clause} WHERE id=?'
                self.cursor.execute(sql, values)
                self.redo_stack.append(operation)
            
            self.conn.commit()
            self.sync()
            return True, f"Operazione annullata: {action}"
            
        except Exception as e:
            print(f"Undo error: {e}")
            return False, f"Errore durante l'annullamento: {e}"
    
    def redo(self) -> Tuple[bool, str]:
        """Ripristina l'ultima operazione annullata"""
        if not self.can_redo():
            return False, "Nessuna operazione da ripristinare"
        
        try:
            operation = self.redo_stack.pop()
            action = operation['action']
            table = operation['table']
            
            if action == 'insert':
                # Redo insert = elimina di nuovo il record
                record_id = operation['id']
                self.cursor.execute(f'DELETE FROM "{table}" WHERE id=?', (record_id,))
                self.undo_stack.append(operation)
                
            elif action == 'delete':
                # Redo delete = elimina di nuovo il record
                record_id = operation['id']
                self.cursor.execute(f'DELETE FROM "{table}" WHERE id=?', (record_id,))
                self.undo_stack.append(operation)
                
            elif action == 'update':
                # Redo update = applica i nuovi valori
                if 'new_data' in operation:
                    record_id = operation['id']
                    new_data = operation['new_data']
                    columns = self.get_columns(table)
                    
                    # Crea update con i nuovi valori
                    col_names = [col[1] for col in columns[1:]]  # Skip ID
                    set_clause = ", ".join([f'"{col}"=?' for col in col_names])
                    values = list(new_data[1:]) + [record_id]
                    sql = f'UPDATE "{table}" SET {set_clause} WHERE id=?'
                    self.cursor.execute(sql, values)
                    self.undo_stack.append(operation)
                else:
                    return False, "Dati insufficienti per ripristinare update"
            
            self.conn.commit()
            self.sync()
            return True, f"Operazione ripristinata: {action}"
            
        except Exception as e:
            print(f"Redo error: {e}")
            return False, f"Errore durante il ripristino: {e}"
    
    def close(self):
        # Prevent double-close
        if getattr(self, '_closed', False):
            return
        self._closed = True

        # Close connection and, if encryption enabled, encrypt temporary DB back to storage
        try:
            if getattr(self, 'conn', None):
                try:
                    # Commit pending transactions
                    self.conn.commit()
                except Exception as e:
                    print(f"Error committing on close: {e}")
                
                try:
                    # Force checkpoint for WAL mode databases to ensure all data is written
                    self.cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except Exception:
                    pass
                
                # Chiudi cursore prima della connessione
                try:
                    self.cursor.close()
                except Exception:
                    pass
                
                try:
                    self.conn.close()
                except Exception as e:
                    print(f"Error closing connection: {e}")
                
                # Assicurati che la connessione sia rilasciata
                self.conn = None
                self.cursor = None
                
        except Exception as e:
            print(f"Error during database close: {e}")

        # Piccola pausa per permettere a Windows di rilasciare i lock sui file
        import time
        time.sleep(0.1)

        if self._uses_encryption:
            try:
                if self._temp_db_file and os.path.exists(self._temp_db_file):
                    # Verifica che il file temporaneo sia valido prima di crittografarlo
                    if os.path.getsize(self._temp_db_file) > 0:
                        # Rimuovi attributi nascosti/sistema dal file .enc per poterlo sovrascrivere
                        if os.path.exists(self.encrypted_path):
                            _clear_file_attributes(self.encrypted_path)
                        self._encrypt_file(self._temp_db_file, self.encrypted_path)
                        # Nascondi il file crittografato
                        _set_hidden_system_attributes(self.encrypted_path)
                    else:
                        print("Warning: temp database file is empty, skipping encryption")
                elif os.path.exists(self.db_path):
                    if os.path.exists(self.encrypted_path):
                        _clear_file_attributes(self.encrypted_path)
                    self._encrypt_file(self.db_path, self.encrypted_path)
                    _set_hidden_system_attributes(self.encrypted_path)
            except Exception as e:
                print(f"Error encrypting database on close: {e}")
            finally:
                # Rimuovi file temporaneo con retry
                if self._temp_db_file and self._temp_db_file != self.db_path:
                    for attempt in range(3):
                        try:
                            if os.path.exists(self._temp_db_file):
                                os.remove(self._temp_db_file)
                            # Rimuovi anche eventuali file WAL/SHM
                            for suffix in ['-wal', '-shm']:
                                wal_file = self._temp_db_file + suffix
                                if os.path.exists(wal_file):
                                    os.remove(wal_file)
                            break
                        except Exception as e:
                            if attempt == 2:
                                print(f"Error removing temp file: {e}")
                            time.sleep(0.1)
