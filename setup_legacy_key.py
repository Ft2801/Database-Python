#!/usr/bin/env python3
"""
Setup script per configurare la chiave legacy di crittografia.

Eseguire questo script SOLO se:
1. Hai file criptati con una vecchia versione dell'applicazione
2. Non riesci ad aprire questi file con la nuova versione
3. Conosci la chiave legacy utilizzata in precedenza

Per nuove installazioni, NON è necessario eseguire questo script.
"""

import os
import sys

def get_data_dir(app_name: str = "DatabasePro") -> str:
    """Return the data directory for storing keys."""
    try:
        program_data = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
        path = os.path.join(program_data, app_name)
        os.makedirs(path, exist_ok=True)
        return path
    except Exception:
        return os.getcwd()


def setup_legacy_key():
    """Setup della chiave legacy per retrocompatibilità."""
    print("=" * 70)
    print("Gestione Database - Setup Chiave Legacy")
    print("=" * 70)
    print()
    print("Questo script configura una chiave legacy per decrittare file vecchi.")
    print("Se stai iniziando da zero, NON hai bisogno di questo script.")
    print()
    
    response = input("Hai file criptati con una vecchia chiave? (s/n): ").strip().lower()
    
    if response != 's':
        print("\n✓ Non è necessaria alcuna configurazione legacy.")
        print("  L'applicazione genererà automaticamente nuove chiavi sicure.")
        return
    
    print("\n" + "-" * 70)
    print("Opzioni disponibili:")
    print("1. Inserisci una chiave legacy esistente (formato base64)")
    print("2. Genera una nuova chiave (per test o nuova configurazione)")
    print("3. Annulla")
    print("-" * 70)
    
    choice = input("\nScegli un'opzione (1-3): ").strip()
    
    if choice == '1':
        print("\nInserisci la chiave legacy nel formato:")
        print("  b'...' oppure solo il contenuto base64")
        print("\nEsempio: IfjQ3BX0Kl36g3jC-rFj2_9bHmP8zc6gAt0J1jskRwA=")
        
        key_input = input("\nChiave: ").strip()
        
        # Parse input
        if key_input.startswith("b'") and key_input.endswith("'"):
            key_input = key_input[2:-1]
        elif key_input.startswith('b"') and key_input.endswith('"'):
            key_input = key_input[2:-1]
        
        # Validate base64
        try:
            key_bytes = key_input.encode('utf-8')
            
            # Try to validate with Fernet
            try:
                from cryptography.fernet import Fernet
                Fernet(key_bytes)  # Validates the key format
            except Exception as e:
                print(f"\n❌ Chiave non valida: {e}")
                return
            
            legacy_key = key_bytes
            
        except Exception as e:
            print(f"\n❌ Formato chiave non valido: {e}")
            return
    
    elif choice == '2':
        try:
            from cryptography.fernet import Fernet
            legacy_key = Fernet.generate_key()
            print(f"\n✓ Nuova chiave generata: {legacy_key.decode('utf-8')}")
            print("  (Salva questa chiave in un posto sicuro!)")
        except ImportError:
            print("\n❌ cryptography non installato!")
            print("   Installa con: pip install cryptography")
            return
    
    elif choice == '3':
        print("\n✓ Operazione annullata.")
        return
    
    else:
        print("\n❌ Scelta non valida.")
        return
    
    # Save the key
    try:
        data_dir = get_data_dir()
        legacy_key_path = os.path.join(data_dir, 'legacy_key.key')
        
        with open(legacy_key_path, 'wb') as f:
            f.write(legacy_key)
        
        # Set restricted permissions
        try:
            os.chmod(legacy_key_path, 0o600)
        except Exception:
            pass
        
        # Hide file on Windows
        try:
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            FILE_ATTRIBUTE_SYSTEM = 0x04
            ctypes.windll.kernel32.SetFileAttributesW(
                legacy_key_path, 
                FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
            )
        except Exception:
            pass
        
        print(f"\n✓ Chiave legacy salvata in: {legacy_key_path}")
        print("  (File nascosto e protetto)")
        print("\nI tuoi file vecchi verranno automaticamente migrati alla nuova")
        print("crittografia quando li aprirai la prima volta.")
        
    except Exception as e:
        print(f"\n❌ Errore nel salvare la chiave: {e}")
        return


def main():
    try:
        setup_legacy_key()
    except KeyboardInterrupt:
        print("\n\n✓ Operazione interrotta dall'utente.")
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
