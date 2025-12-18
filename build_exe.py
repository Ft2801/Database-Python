"""
Script per creare l'eseguibile dell'applicazione DatabasePro.
Usa PyInstaller per creare un singolo file .exe
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
    
    # File da includere (solo il logo, gli altri file sono creati dall'app in ProgramData)
    added_files = [
        ("logo.png", "."),
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
        # Moduli per l'auto-aggiornamento
        "updater",
        "urllib",
        "urllib.request",
        "urllib.error",
        "json",
        "tempfile",
        "threading",
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
        
        # Ottieni la dimensione del file
        exe_path = os.path.join("dist", f"{app_name}.exe")
        size_mb = os.path.getsize(exe_path) / (1024 * 1024) if os.path.exists(exe_path) else 0
        
        print("\n" + "=" * 60)
        print("✓ BUILD COMPLETATO!")
        print("=" * 60)
        print(f"\nFile: dist\\{app_name}.exe ({size_mb:.1f} MB)")
        print("\nPer creare l'installer, esegui:")
        print("  python build_installer.py")
        
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("✗ ERRORE DURANTE LA BUILD")
        print("=" * 60)
        print(e.stderr)
        sys.exit(1)


if __name__ == "__main__":
    build_executable()
