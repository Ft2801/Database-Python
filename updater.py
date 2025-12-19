"""
Modulo per l'auto-aggiornamento dell'applicazione DatabasePro.
Controlla le release su GitHub e scarica/installa automaticamente gli aggiornamenti.
"""
import os
import sys
import json
import tempfile
import subprocess
import threading
import time
import glob
import psutil
from typing import Optional, Tuple, Callable
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# Configurazione GitHub
GITHUB_OWNER = "Ft2801"
GITHUB_REPO = "Database-Python"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
INSTALLER_NAME = "DatabasePro_Setup.exe"

# Versione corrente dell'applicazione (da aggiornare ad ogni release)
CURRENT_VERSION = "1.1.1"

# Configurazione per il monitoraggio dell'installer
INSTALLER_MONITOR_TIMEOUT = 600  # Timeout massimo in secondi per il monitoraggio (10 minuti)
INSTALLER_CHECK_INTERVAL = 5  # Intervallo in secondi per controllare lo stato del file


def find_old_installer_files() -> list:
    """
    Trova tutti i file installer ancora presenti nella cartella temporanea.
    
    Returns:
        Lista di percorsi ai file installer trovati.
    """
    try:
        temp_dir = tempfile.gettempdir()
        # Pattern per trovare i file installer
        patterns = [
            os.path.join(temp_dir, "DatabasePro_Setup_*.exe"),
            os.path.join(temp_dir, "DatabasePro_Setup.exe")
        ]
        
        installer_files = []
        for pattern in patterns:
            installer_files.extend(glob.glob(pattern))
        
        print(f"[Updater] Trovati {len(installer_files)} file installer nella cartella temporanea")
        return installer_files
    except Exception as e:
        print(f"[Updater] Errore durante la ricerca dei file installer: {e}")
        return []


def cleanup_old_installers() -> Tuple[int, int]:
    """
    Elimina tutti i vecchi file installer dalla cartella temporanea.
    
    Returns:
        Tupla (file_eliminati, file_falliti) con il numero di file eliminati e falliti.
    """
    old_files = find_old_installer_files()
    if not old_files:
        return 0, 0
    
    deleted_count = 0
    failed_count = 0
    
    for file_path in old_files:
        try:
            # Verifica se il file è in uso
            if os.path.exists(file_path):
                try:
                    # Prova a verificare se il file è accessibile (in lettura, senza modificarlo)
                    with open(file_path, 'rb'):
                        pass
                    # Se arriviamo qui, possiamo eliminarlo
                    os.remove(file_path)
                    print(f"[Updater] File installer eliminato: {file_path}")
                    deleted_count += 1
                except PermissionError:
                    # File probabilmente in uso
                    print(f"[Updater] File installer in uso, impossibile eliminare: {file_path}")
                    failed_count += 1
                except Exception as e:
                    print(f"[Updater] Errore durante l'eliminazione di {file_path}: {e}")
                    failed_count += 1
        except Exception as e:
            print(f"[Updater] Errore generico durante la pulizia di {file_path}: {e}")
            failed_count += 1
    
    print(f"[Updater] Pulizia completata: {deleted_count} eliminati, {failed_count} falliti")
    return deleted_count, failed_count


def safe_delete_file(file_path: str, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """
    Tenta di eliminare un file in modo sicuro con retry.
    
    Args:
        file_path: Percorso del file da eliminare
        max_retries: Numero massimo di tentativi
        retry_delay: Ritardo in secondi tra i tentativi
    
    Returns:
        True se il file è stato eliminato con successo, False altrimenti.
    """
    if not os.path.exists(file_path):
        return True  # File già eliminato
    
    for attempt in range(max_retries):
        try:
            os.remove(file_path)
            print(f"[Updater] File eliminato con successo: {file_path}")
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(f"[Updater] Tentativo {attempt + 1}/{max_retries} fallito (file in uso), riprovo tra {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"[Updater] Impossibile eliminare il file dopo {max_retries} tentativi: {e}")
                return False
        except Exception as e:
            print(f"[Updater] Errore durante l'eliminazione del file: {e}")
            return False
    
    return False


def monitor_installer_process(installer_path: str, process_handle=None):
    """
    Monitora il processo installer e pulisce il file quando termina.
    Questa funzione viene eseguita in un thread separato.
    
    Args:
        installer_path: Percorso del file installer da monitorare e eliminare
        process_handle: Handle del processo (opzionale, usato su Windows)
    """
    try:
        print(f"[Updater] Inizio monitoraggio installer: {installer_path}")
        
        # Su Windows, se abbiamo l'handle del processo, lo usiamo
        if sys.platform == 'win32' and process_handle:
            try:
                # Usa psutil per monitorare il processo se possibile
                if isinstance(process_handle, int):
                    # È un PID
                    try:
                        process = psutil.Process(process_handle)
                        process.wait(timeout=None)  # Attendi che il processo termini
                        print(f"[Updater] Processo installer terminato (PID: {process_handle})")
                    except psutil.NoSuchProcess:
                        print(f"[Updater] Processo non trovato (già terminato?)")
                    except Exception as e:
                        print(f"[Updater] Errore monitoraggio processo: {e}")
                        # Fallback: attendi un po' e prova a eliminare
                        time.sleep(5)
            except Exception as e:
                print(f"[Updater] Errore nell'uso di psutil: {e}")
                # Fallback: attendi e controlla periodicamente
                elapsed = 0
                
                while elapsed < INSTALLER_MONITOR_TIMEOUT:
                    time.sleep(INSTALLER_CHECK_INTERVAL)
                    elapsed += INSTALLER_CHECK_INTERVAL
                    
                    # Controlla se il file è ancora in uso (lettura, non modifica)
                    try:
                        with open(installer_path, 'rb'):
                            # Se riusciamo ad aprirlo in lettura, probabilmente non è più in uso
                            break
                    except Exception:
                        continue
        else:
            # Su Unix o senza handle, attendi un po' e prova a eliminare
            time.sleep(10)
        
        # Attendi un po' prima di provare a eliminare per sicurezza
        time.sleep(2)
        
        # Tenta di eliminare il file
        print(f"[Updater] Tentativo di eliminazione del file installer...")
        success = safe_delete_file(installer_path, max_retries=5, retry_delay=2.0)
        
        if success:
            print(f"[Updater] File installer eliminato con successo")
        else:
            print(f"[Updater] Impossibile eliminare il file installer, verrà rimosso al prossimo avvio")
    
    except Exception as e:
        print(f"[Updater] Errore durante il monitoraggio del processo installer: {e}")


def get_current_version() -> str:
    """Restituisce la versione corrente dell'applicazione."""
    return CURRENT_VERSION


def parse_version(version_str: str) -> Tuple[int, ...]:
    """
    Converte una stringa di versione in una tupla di interi per il confronto.
    Supporta formati come: 1.0.0, v1.0.0, 1.2.3-beta
    """
    # Rimuovi prefisso 'v' se presente
    version_str = version_str.strip().lower()
    if version_str.startswith('v'):
        version_str = version_str[1:]
    
    # Rimuovi suffissi come -beta, -alpha, -rc
    if '-' in version_str:
        version_str = version_str.split('-')[0]
    
    # Converti in tupla di interi
    try:
        parts = version_str.split('.')
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def is_newer_version(remote_version: str, current_version: str) -> bool:
    """
    Verifica se la versione remota è più recente di quella corrente.
    """
    remote = parse_version(remote_version)
    current = parse_version(current_version)
    return remote > current


def check_for_updates() -> Optional[dict]:
    """
    Controlla se sono disponibili aggiornamenti su GitHub.
    
    Returns:
        dict con informazioni sulla nuova release, oppure None se non ci sono aggiornamenti.
        Il dict contiene: version, download_url, release_notes, published_at
    """
    try:
        # Crea la richiesta con headers appropriati
        request = Request(
            GITHUB_API_URL,
            headers={
                'User-Agent': f'DatabasePro/{CURRENT_VERSION}',
                'Accept': 'application/vnd.github.v3+json'
            }
        )
        
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        # Estrai la versione dalla release
        tag_name = data.get('tag_name', '')
        
        # Controlla se è più recente
        if not is_newer_version(tag_name, CURRENT_VERSION):
            return None
        
        # Cerca l'asset dell'installer
        download_url = None
        for asset in data.get('assets', []):
            if asset.get('name', '') == INSTALLER_NAME:
                download_url = asset.get('browser_download_url')
                break
        
        if not download_url:
            # Se non c'è l'installer come asset, potrebbe non essere ancora disponibile
            return None
        
        return {
            'version': tag_name,
            'download_url': download_url,
            'release_notes': data.get('body', ''),
            'published_at': data.get('published_at', ''),
            'html_url': data.get('html_url', '')
        }
    
    except HTTPError as e:
        if e.code == 404:
            # Nessuna release pubblicata - comportamento normale
            print("[Updater] Nessuna release trovata su GitHub (prima release non ancora pubblicata)")
        else:
            print(f"[Updater] Errore HTTP durante il controllo aggiornamenti: {e}")
        return None
    except (URLError, json.JSONDecodeError, KeyError) as e:
        print(f"[Updater] Errore durante il controllo aggiornamenti: {e}")
        return None
    except Exception as e:
        print(f"[Updater] Errore imprevisto: {e}")
        return None


def download_update(download_url: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:
    """
    Scarica l'installer dalla URL specificata.
    
    Args:
        download_url: URL del file da scaricare
        progress_callback: Funzione opzionale chiamata con (bytes_scaricati, bytes_totali)
    
    Returns:
        Percorso del file scaricato, oppure None in caso di errore.
    """
    try:
        request = Request(
            download_url,
            headers={
                'User-Agent': f'DatabasePro/{CURRENT_VERSION}'
            }
        )
        
        with urlopen(request, timeout=60) as response:
            # Ottieni la dimensione totale
            total_size = int(response.headers.get('Content-Length', 0))
            
            # Crea un file temporaneo per il download
            # Usiamo un nome che include la versione per evitare conflitti con file bloccati
            temp_dir = tempfile.gettempdir()
            # Rimuoviamo eventuali caratteri non validi dalla versione per il nome file
            safe_version = download_url.split('/')[-2].replace('.', '_')
            temp_filename = f"DatabasePro_Setup_{safe_version}.exe"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Se il file esiste già, proviamo a rimuoverlo
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    # Se non riusciamo a rimuoverlo (magari è in uso), usiamo un nome unico
                    import time
                    temp_path = os.path.join(temp_dir, f"DatabasePro_Setup_{int(time.time())}.exe")
            
            # Scarica il file
            downloaded = 0
            block_size = 8192
            
            with open(temp_path, 'wb') as f:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    
                    downloaded += len(buffer)
                    f.write(buffer)
                    
                    if progress_callback:
                        progress_callback(downloaded, total_size)
            
            # Verifica che il file sia stato scaricato completamente
            if total_size > 0 and downloaded < total_size:
                print(f"[Updater] Download incompleto: {downloaded}/{total_size} bytes")
                return None
            
            print(f"[Updater] Download completato: {temp_path} ({downloaded} bytes)")
            return temp_path
    
    except (URLError, HTTPError, IOError) as e:
        print(f"[Updater] Errore durante il download: {e}")
        return None
    except Exception as e:
        print(f"[Updater] Errore imprevisto durante il download: {e}")
        return None


def install_update(installer_path: str, start_monitoring: bool = True) -> Tuple[bool, str]:
    """
    Esegue l'installer per aggiornare l'applicazione.
    
    Args:
        installer_path: Percorso del file installer
        start_monitoring: Se True, avvia il monitoraggio del processo per la pulizia automatica
    
    Returns:
        (Successo, Messaggio di errore o stato)
    """
    try:
        if not os.path.exists(installer_path):
            return False, f"Installer non trovato: {installer_path}"
        
        installer_path = os.path.abspath(installer_path)
        print(f"[Updater] Avvio installer: {installer_path}")
        
        process_info = None  # Per salvare informazioni sul processo
        
        if sys.platform == 'win32':
            try:
                import ctypes
                # SW_SHOWNORMAL = 1
                print(f"[Updater] Tentativo avvio con ShellExecuteW (runas): {installer_path}")
                result = ctypes.windll.shell32.ShellExecuteW(None, "runas", installer_path, None, None, 1)
                if result > 32:
                    print(f"[Updater] ShellExecuteW riuscito (codice: {result})")
                    # Avvia il monitoraggio in background
                    if start_monitoring:
                        monitor_thread = threading.Thread(
                            target=monitor_installer_process,
                            args=(installer_path, None),
                            daemon=True
                        )
                        monitor_thread.start()
                    return True, "Installer avviato con successo"
                else:
                    raise Exception(f"Errore ShellExecuteW: {result}")
            except Exception as e:
                print(f"[Updater] ShellExecuteW fallito: {e}")
                try:
                    os.startfile(installer_path)
                    print("[Updater] Installer avviato con os.startfile")
                    # Avvia il monitoraggio in background
                    if start_monitoring:
                        monitor_thread = threading.Thread(
                            target=monitor_installer_process,
                            args=(installer_path, None),
                            daemon=True
                        )
                        monitor_thread.start()
                    return True, "Installer avviato con os.startfile"
                except Exception as e2:
                    print(f"[Updater] os.startfile fallito: {e2}")
                    try:
                        proc = subprocess.Popen(f'"{installer_path}"', shell=True)
                        process_info = proc.pid
                        print(f"[Updater] Installer avviato con subprocess (PID: {process_info})")
                        # Avvia il monitoraggio in background
                        if start_monitoring:
                            monitor_thread = threading.Thread(
                                target=monitor_installer_process,
                                args=(installer_path, process_info),
                                daemon=True
                            )
                            monitor_thread.start()
                        return True, "Installer avviato con subprocess"
                    except Exception as e3:
                        print(f"[Updater] Tutti i tentativi falliti: {e3}")
                        return False, f"Tutti i tentativi falliti. Errore finale: {e3}"
        else:
            try:
                os.chmod(installer_path, 0o755)
                proc = subprocess.Popen([installer_path], start_new_session=True)
                process_info = proc.pid
                print(f"[Updater] Installer avviato (PID: {process_info})")
                # Avvia il monitoraggio in background
                if start_monitoring:
                    monitor_thread = threading.Thread(
                        target=monitor_installer_process,
                        args=(installer_path, process_info),
                        daemon=True
                    )
                    monitor_thread.start()
                return True, "Installer avviato"
            except Exception as e:
                return False, f"Errore avvio Unix: {e}"
    
    except Exception as e:
        return False, f"Errore critico: {e}"


def check_and_update_async(
    on_update_available: Optional[Callable[[dict], None]] = None,
    on_no_update: Optional[Callable[[], None]] = None,
    on_error: Optional[Callable[[str], None]] = None
):
    """
    Controlla gli aggiornamenti in modo asincrono (in un thread separato).
    
    Args:
        on_update_available: Callback chiamato se c'è un aggiornamento (riceve info release)
        on_no_update: Callback chiamato se non ci sono aggiornamenti
        on_error: Callback chiamato in caso di errore (riceve messaggio errore)
    """
    def _check():
        try:
            update_info = check_for_updates()
            if update_info:
                if on_update_available:
                    on_update_available(update_info)
            else:
                if on_no_update:
                    on_no_update()
        except Exception as e:
            if on_error:
                on_error(str(e))
    
    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
    return thread


class UpdateChecker:
    """
    Classe per gestire il controllo e l'installazione degli aggiornamenti
    con integrazione PyQt6.
    """
    
    def __init__(self):
        self.update_info = None
        self.download_path = None
    
    def check_for_updates_sync(self) -> Optional[dict]:
        """Controlla gli aggiornamenti in modo sincrono."""
        self.update_info = check_for_updates()
        return self.update_info
    
    def download_update_sync(self, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """Scarica l'aggiornamento in modo sincrono."""
        if not self.update_info:
            return False
        
        self.download_path = download_update(
            self.update_info['download_url'],
            progress_callback
        )
        return self.download_path is not None
    
    def install_update(self) -> bool:
        """Installa l'aggiornamento scaricato."""
        if not self.download_path:
            return False
        return install_update(self.download_path)
    
    def get_update_info(self) -> Optional[dict]:
        """Restituisce le informazioni sull'aggiornamento disponibile."""
        return self.update_info


# Per test da riga di comando
if __name__ == "__main__":
    print(f"Versione corrente: {CURRENT_VERSION}")
    print("Controllo aggiornamenti...")
    
    update_info = check_for_updates()
    
    if update_info:
        print(f"\n✓ Nuova versione disponibile: {update_info['version']}")
        print(f"  URL download: {update_info['download_url']}")
        print(f"  Pubblicato: {update_info['published_at']}")
        if update_info['release_notes']:
            print(f"\nNote di rilascio:\n{update_info['release_notes'][:500]}...")
    else:
        print("\n✓ L'applicazione è già aggiornata alla versione più recente.")
