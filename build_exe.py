"""
Script per creare l'eseguibile dell'applicazione Gestione Database usando PyInstaller
"""
import os
import subprocess
import sys

def build_executable():
    """Crea l'eseguibile dell'applicazione"""
    
    print("=" * 60)
    print("Gestione Database - Build Eseguibile")
    print("=" * 60)
    
    # Verifica che PyInstaller sia installato
    try:
        import PyInstaller
        print("✓ PyInstaller trovato")
    except ImportError:
        print("✗ PyInstaller non trovato. Installazione in corso...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installato")
    
    # Parametri per PyInstaller
    app_name = "DatabasePro"
    main_script = "app.py"
    icon_file = "logo.png"
    
    # File da includere
    added_files = [
        ("logo.png", "."),
        ("app_config.json", "."),
        ("files", "files"),  # Cartella per gli allegati ai record
    ]
    
    # Costruisci il comando PyInstaller
    cmd = [
        "pyinstaller",
        "--name", app_name,
        "--windowed",  # Non mostra console
        "--onefile",   # Crea un singolo file eseguibile
        "--clean",     # Pulisce cache
    ]
    
    # Aggiungi l'icona se esiste
    if os.path.exists(icon_file):
        # PyInstaller richiede .ico su Windows, convertiamo il PNG
        print(f"✓ Logo trovato: {icon_file}")
        try:
            from PIL import Image
            img = Image.open(icon_file)
            ico_path = "logo.ico"
            img.save(ico_path, format='ICO', sizes=[(256, 256)])
            cmd.extend(["--icon", ico_path])
            print(f"✓ Icona convertita in {ico_path}")
        except Exception as e:
            print(f"⚠ Impossibile convertire l'icona: {e}")
    
    # Aggiungi file da includere
    for src, dest in added_files:
        if os.path.exists(src):
            # Su Windows, PyInstaller usa ; come separatore
            cmd.extend(["--add-data", f"{src};{dest}"])
            print(f"✓ Aggiunto: {src}")
        else:
            print(f"⚠ File non trovato (sarà ignorato): {src}")
    
    # Aggiungi moduli nascosti necessari
    hidden_imports = [
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "sqlite3",
        "cryptography",
        "cryptography.fernet",
        "cryptography.hazmat.primitives",
        "cryptography.hazmat.primitives.kdf",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "cryptography.hazmat.backends",
        "cryptography.hazmat.backends.openssl",
    ]
    
    for module in hidden_imports:
        cmd.extend(["--hidden-import", module])
    
    # Aggiungi lo script principale
    cmd.append(main_script)
    
    print("\n" + "=" * 60)
    print("Esecuzione PyInstaller...")
    print("=" * 60)
    print(f"Comando: {' '.join(cmd)}\n")
    
    try:
        # Esegui PyInstaller
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        print("\n" + "=" * 60)
        print("✓ BUILD COMPLETATO CON SUCCESSO!")
        print("=" * 60)
        print(f"\nL'eseguibile si trova in: dist\\{app_name}.exe")
        print("\nFile generati:")
        print(f"  - dist\\{app_name}.exe (eseguibile)")
        print(f"  - build\\ (file temporanei)")
        print(f"  - {app_name}.spec (configurazione)")
        
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("✗ ERRORE DURANTE LA BUILD")
        print("=" * 60)
        print(e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build_executable()
