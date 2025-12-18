"""
Script per creare l'installer di DatabasePro.
L'installer include l'exe dell'applicazione al suo interno.
Compila automaticamente l'exe se non esiste.
"""
import os
import subprocess
import sys
import shutil


def build_app_exe():
    """Compila l'exe dell'applicazione"""
    print("\n" + "-" * 60)
    print("Compilazione DatabasePro.exe...")
    print("-" * 60)
    
    # Importa ed esegue la funzione di build
    from build_exe import build_executable
    build_executable()
    
    # Verifica che sia stato creato
    exe_path = os.path.join("dist", "DatabasePro.exe")
    return os.path.exists(exe_path)


def ensure_exe_exists():
    """Verifica che l'exe esista, altrimenti lo compila"""
    exe_path = os.path.join("dist", "DatabasePro.exe")
    if not os.path.exists(exe_path):
        print("⚠ DatabasePro.exe non trovato, lo compilo ora...")
        if not build_app_exe():
            print("✗ Errore durante la compilazione dell'exe")
            return False
    return True


def build_installer():
    """Crea l'installer che include l'exe embedded"""
    
    print("=" * 60)
    print("DatabasePro - Build Installer")
    print("=" * 60)
    
    # Verifica/compila l'exe
    if not ensure_exe_exists():
        sys.exit(1)
    
    # Verifica PyInstaller
    try:
        import PyInstaller
        print("✓ PyInstaller trovato")
    except ImportError:
        print("✗ PyInstaller non trovato. Installazione in corso...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installato")
    
    print("✓ DatabasePro.exe pronto")
    
    # Comando per creare l'installer Python
    # Includiamo l'exe come dato aggiuntivo
    cmd = [
        "pyinstaller",
        "--name", "DatabasePro_Setup",
        "--windowed",
        "--onefile",
        "--clean",
        "--uac-admin",  # Richiede privilegi di amministratore
        "--add-data", "dist\\DatabasePro.exe;.",  # Include l'exe nell'installer
    ]
    
    # Aggiungi l'icona se esiste
    if os.path.exists("logo.ico"):
        cmd.extend(["--icon", "logo.ico"])
        cmd.extend(["--add-data", "logo.ico;."])
        print("✓ Icona trovata")
    
    if os.path.exists("logo.png"):
        cmd.extend(["--add-data", "logo.png;."])
    
    cmd.append("installer_gui.py")
    
    print("\n" + "=" * 60)
    print("Creazione Installer...")
    print("=" * 60)
    print(f"Comando: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        installer_path = os.path.join("dist", "DatabasePro_Setup.exe")
        if os.path.exists(installer_path):
            # Ottieni la dimensione del file
            size_mb = os.path.getsize(installer_path) / (1024 * 1024)
            
            print("\n" + "=" * 60)
            print("✓ INSTALLER CREATO CON SUCCESSO!")
            print("=" * 60)
            print(f"\nFile: dist\\DatabasePro_Setup.exe ({size_mb:.1f} MB)")
            print("\nQuesto installer:")
            print("  - Include l'applicazione DatabasePro.exe")
            print("  - Richiede privilegi di amministratore")
            print("  - Preserva i dati utente esistenti")
            print("  - Crea collegamenti sul desktop e menu Start")
            return True
            
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("✗ ERRORE DURANTE LA BUILD")
        print("=" * 60)
        print(e.stderr if e.stderr else str(e))
        sys.exit(1)
    
    return False


if __name__ == "__main__":
    build_installer()
