"""
Script per preparare una nuova release di DatabasePro.

Questo script:
1. Compila l'installer (build_installer.py)
2. Chiede la nuova versione (formato x.x.x)
3. Chiede un messaggio di changelog opzionale
4. Aggiorna il file CHANGELOG.md
5. Aggiorna la versione in updater.py

Dopo l'esecuzione, pubblicare manualmente la commit su GitHub
e creare la release con l'installer allegato.
"""
import os
import re
import sys
import subprocess
from datetime import datetime


UPDATER_FILE = "updater.py"
INSTALLER_GUI_FILE = "installer_gui.py"
CHANGELOG_FILE = "CHANGELOG.md"
VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')


def validate_version(version: str) -> bool:
    """Verifica che la versione sia nel formato x.x.x"""
    return bool(VERSION_PATTERN.match(version.strip()))


def get_current_version() -> str:
    """Legge la versione corrente dal file updater.py"""
    try:
        with open(UPDATER_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    except FileNotFoundError:
        pass
    return "0.0.0"


def update_version_in_updater(new_version: str):
    """Aggiorna la versione nel file updater.py"""
    with open(UPDATER_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(
        r'CURRENT_VERSION\s*=\s*["\'][^"\']+["\']',
        f'CURRENT_VERSION = "{new_version}"',
        content
    )
    
    with open(UPDATER_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)


def update_version_in_installer_gui(new_version: str):
    """Aggiorna la versione nel file installer_gui.py"""
    with open(INSTALLER_GUI_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(
        r'APP_VERSION\s*=\s*["\'][^"\']+["\']',
        f'APP_VERSION = "{new_version}"',
        content
    )
    
    with open(INSTALLER_GUI_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)


def update_changelog(version: str, message: str):
    """Aggiunge una nuova entry al changelog"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Leggi il changelog esistente
    try:
        with open(CHANGELOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = "# Changelog\n\nTutte le modifiche importanti a DatabasePro saranno documentate in questo file.\n\n---\n"
    
    # Prepara la nuova entry
    if message.strip():
        new_entry = f"""
## [{version}] - {today}

### Modifiche
- {message}
"""
    else:
        new_entry = f"""
## [{version}] - {today}

### Modifiche
- Aggiornamento alla versione {version}
"""
    
    # Trova la posizione dopo "---" iniziale per inserire la nuova entry
    lines = content.split('\n')
    insert_index = 0
    found_separator = False
    
    for i, line in enumerate(lines):
        if line.strip() == '---' and not found_separator:
            found_separator = True
            insert_index = i + 1
            break
    
    if not found_separator:
        # Se non c'è un separatore, inserisci dopo l'header
        for i, line in enumerate(lines):
            if line.startswith('## ['):
                insert_index = i
                break
            insert_index = len(lines)
    
    # Inserisci la nuova entry
    lines.insert(insert_index, new_entry)
    new_content = '\n'.join(lines)
    
    with open(CHANGELOG_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)


def run_build_installer():
    """Esegue lo script build_installer.py"""
    print("\n" + "=" * 60)
    print("Compilazione installer...")
    print("=" * 60 + "\n")
    
    result = subprocess.run([sys.executable, "build_installer.py"])
    
    if result.returncode != 0:
        print("\n✗ Errore durante la compilazione dell'installer")
        return False
    
    # Verifica che l'installer sia stato creato
    installer_path = os.path.join("dist", "DatabasePro_Setup.exe")
    if not os.path.exists(installer_path):
        print(f"\n✗ Installer non trovato: {installer_path}")
        return False
    
    print("\n✓ Installer compilato con successo")
    return True


def main():
    print("=" * 60)
    print("DatabasePro - Preparazione Release")
    print("=" * 60)
    
    current_version = get_current_version()
    print(f"\nVersione corrente: {current_version}")
    
    # Step 1: Chiedi la nuova versione
    print("\n" + "-" * 60)
    while True:
        new_version = input("\nInserisci la nuova versione (formato x.x.x): ").strip()
        
        if validate_version(new_version):
            break
        else:
            print("✗ Formato non valido. Usa il formato x.x.x (es: 1.2.3)")
    
    # Step 2: Chiedi il messaggio di changelog
    print("\nInserisci il messaggio di changelog (invio per messaggio default):")
    changelog_message = input("> ").strip()
    
    # Step 3: Aggiorna i file di versione PRIMA di compilare l'installer
    print("\n" + "-" * 60)
    print("Aggiornamento file di versione...")
    
    update_version_in_updater(new_version)
    print(f"✓ Versione aggiornata in {UPDATER_FILE}")
    
    update_version_in_installer_gui(new_version)
    print(f"✓ Versione aggiornata in {INSTALLER_GUI_FILE}")
    
    update_changelog(new_version, changelog_message)
    print(f"✓ Changelog aggiornato in {CHANGELOG_FILE}")
    
    # Step 4: Compila l'installer (dopo aver aggiornato le versioni!)
    if not run_build_installer():
        sys.exit(1)
    
    # Step 5: Istruzioni finali
    print("\n" + "=" * 60)
    print("✓ PREPARAZIONE COMPLETATA!")
    print("=" * 60)
    print(f"""
Prossimi passi:

1. Verifica le modifiche:
   git status
   git diff

2. Commit e push:
   git add .
   git commit -m "Release {new_version}"
   git push

3. Crea la release su GitHub:
   - Vai su: https://github.com/Ft2801/Database-Python/releases/new
   - Tag: v{new_version}
   - Titolo: DatabasePro {new_version}
   - Allega: dist\\DatabasePro_Setup.exe
   - Pubblica la release

L'installer si trova in: dist\\DatabasePro_Setup.exe
""")


if __name__ == "__main__":
    main()
