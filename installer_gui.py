"""
Installer Python per DatabasePro
Questo script viene compilato come exe separato e funge da installer.
Richiede privilegi di amministratore per installare in Program Files.
"""
import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import tempfile
import ctypes

# Configurazione
APP_NAME = "DatabasePro"
APP_VERSION = "1.1.2"
DEFAULT_INSTALL_DIR = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), APP_NAME)


def is_admin():
    """Verifica se il processo è in esecuzione come amministratore"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Rilancia il programma con privilegi di amministratore"""
    try:
        if getattr(sys, 'frozen', False):
            # Siamo in un exe
            script = sys.executable
        else:
            # Siamo in sviluppo
            script = os.path.abspath(__file__)
        
        # Usa ShellExecuteW per richiedere elevazione UAC
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable if not getattr(sys, 'frozen', False) else script,
            " ".join(sys.argv[1:]) if not getattr(sys, 'frozen', False) else "",
            None, 1
        )
        return True
    except Exception as e:
        return False


class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Installazione {APP_NAME}")
        self.root.geometry("550x400")
        self.root.resizable(False, False)
        
        # Centra la finestra
        self.center_window()
        
        # Variabili
        self.install_dir = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.create_desktop_shortcut = tk.BooleanVar(value=True)
        self.create_start_menu = tk.BooleanVar(value=True)
        
        # Stato corrente
        self.current_page = 0
        self.pages = []
        
        # Container principale
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Crea le pagine
        self.create_welcome_page()
        self.create_directory_page()
        self.create_options_page()
        self.create_install_page()
        self.create_finish_page()
        
        # Pulsanti di navigazione
        self.nav_frame = ttk.Frame(self.root)
        self.nav_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.back_btn = ttk.Button(self.nav_frame, text="< Indietro", command=self.go_back)
        self.back_btn.pack(side=tk.LEFT)
        
        self.cancel_btn = ttk.Button(self.nav_frame, text="Annulla", command=self.cancel)
        self.cancel_btn.pack(side=tk.LEFT, padx=10)
        
        self.next_btn = ttk.Button(self.nav_frame, text="Avanti >", command=self.go_next)
        self.next_btn.pack(side=tk.RIGHT)
        
        # Mostra la prima pagina
        self.show_page(0)
    
    def center_window(self):
        self.root.update_idletasks()
        width = 550
        height = 400
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_welcome_page(self):
        page = ttk.Frame(self.main_frame)
        
        # Titolo
        title = ttk.Label(page, text=f"Benvenuto nell'installazione di {APP_NAME}",
                         font=('Segoe UI', 14, 'bold'))
        title.pack(pady=20)
        
        # Descrizione
        desc = ttk.Label(page, text=f"""Questo programma installerà {APP_NAME} versione {APP_VERSION}
sul tuo computer.

NOTA IMPORTANTE:
I tuoi dati esistenti NON verranno modificati:
  • Database
  • Password di accesso  
  • File allegati
  • Chiavi di crittografia

Si consiglia di chiudere tutte le altre applicazioni
prima di continuare.""", justify=tk.LEFT)
        desc.pack(pady=20, padx=20)
        
        self.pages.append(page)
    
    def create_directory_page(self):
        page = ttk.Frame(self.main_frame)
        
        title = ttk.Label(page, text="Seleziona la cartella di installazione",
                         font=('Segoe UI', 12, 'bold'))
        title.pack(pady=20)
        
        desc = ttk.Label(page, text=f"{APP_NAME} verrà installato nella seguente cartella.\n"
                                    "Per installare in una cartella diversa, clicca Sfoglia.")
        desc.pack(pady=10)
        
        dir_frame = ttk.Frame(page)
        dir_frame.pack(fill=tk.X, padx=20, pady=10)
        
        dir_entry = ttk.Entry(dir_frame, textvariable=self.install_dir, width=50)
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = ttk.Button(dir_frame, text="Sfoglia...", command=self.browse_directory)
        browse_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Spazio richiesto
        space_label = ttk.Label(page, text="Spazio richiesto: ~50 MB")
        space_label.pack(pady=20)
        
        self.pages.append(page)
    
    def create_options_page(self):
        page = ttk.Frame(self.main_frame)
        
        title = ttk.Label(page, text="Opzioni di installazione",
                         font=('Segoe UI', 12, 'bold'))
        title.pack(pady=20)
        
        # Checkbox per le opzioni
        desktop_cb = ttk.Checkbutton(page, text="Crea icona sul Desktop",
                                     variable=self.create_desktop_shortcut)
        desktop_cb.pack(anchor=tk.W, padx=40, pady=5)
        
        startmenu_cb = ttk.Checkbutton(page, text="Crea voce nel Menu Start",
                                       variable=self.create_start_menu)
        startmenu_cb.pack(anchor=tk.W, padx=40, pady=5)
        
        self.pages.append(page)
    
    def create_install_page(self):
        page = ttk.Frame(self.main_frame)
        
        title = ttk.Label(page, text="Installazione in corso...",
                         font=('Segoe UI', 12, 'bold'))
        title.pack(pady=20)
        
        self.progress_label = ttk.Label(page, text="Preparazione...")
        self.progress_label.pack(pady=10)
        
        self.progress_bar = ttk.Progressbar(page, length=400, mode='determinate')
        self.progress_bar.pack(pady=20)
        
        self.status_label = ttk.Label(page, text="")
        self.status_label.pack(pady=10)
        
        self.pages.append(page)
    
    def create_finish_page(self):
        page = ttk.Frame(self.main_frame)
        
        title = ttk.Label(page, text="Installazione completata!",
                         font=('Segoe UI', 14, 'bold'))
        title.pack(pady=20)
        
        desc = ttk.Label(page, text=f"""{APP_NAME} è stato installato con successo.

I tuoi dati esistenti sono stati preservati.

Clicca 'Fine' per chiudere l'installazione.""", justify=tk.LEFT)
        desc.pack(pady=20, padx=20)
        
        self.launch_cb_var = tk.BooleanVar(value=True)
        launch_cb = ttk.Checkbutton(page, text=f"Avvia {APP_NAME}",
                                    variable=self.launch_cb_var)
        launch_cb.pack(pady=10)
        
        self.pages.append(page)
    
    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.install_dir.get())
        if directory:
            self.install_dir.set(directory)
    
    def show_page(self, index):
        # Nascondi tutte le pagine
        for page in self.pages:
            page.pack_forget()
        
        # Mostra la pagina corrente
        self.pages[index].pack(fill=tk.BOTH, expand=True)
        self.current_page = index
        
        # Aggiorna i pulsanti
        self.back_btn.config(state=tk.NORMAL if index > 0 else tk.DISABLED)
        
        if index == len(self.pages) - 1:
            # Pagina finale - abilita Fine e nascondi Indietro
            self.next_btn.config(text="Fine", state=tk.NORMAL)
            self.back_btn.config(state=tk.DISABLED)
            self.cancel_btn.config(state=tk.DISABLED)
        elif index == 3:  # Pagina di installazione
            self.next_btn.config(text="Installa", state=tk.NORMAL)
            self.back_btn.config(state=tk.DISABLED)
        else:
            self.next_btn.config(text="Avanti >", state=tk.NORMAL)
    
    def go_back(self):
        if self.current_page > 0:
            self.show_page(self.current_page - 1)
    
    def go_next(self):
        if self.current_page == len(self.pages) - 1:
            # Ultima pagina - chiudi e avvia l'app se richiesto
            if self.launch_cb_var.get():
                exe_path = os.path.join(self.install_dir.get(), f"{APP_NAME}.exe")
                if os.path.exists(exe_path):
                    subprocess.Popen([exe_path])
            self.root.quit()
        elif self.current_page == 2:
            # Pagina opzioni -> vai a installazione
            self.show_page(3)
            self.root.after(100, self.perform_installation)
        else:
            self.show_page(self.current_page + 1)
    
    def cancel(self):
        if messagebox.askyesno("Annulla", "Sei sicuro di voler annullare l'installazione?"):
            self.root.quit()
    
    def perform_installation(self):
        """Esegue l'installazione vera e propria"""
        try:
            install_dir = self.install_dir.get()
            
            # Disabilita i pulsanti durante l'installazione
            self.next_btn.config(state=tk.DISABLED)
            self.cancel_btn.config(state=tk.DISABLED)
            
            # Step 1: Crea la directory di installazione
            self.update_progress(10, "Creazione cartella di installazione...")
            os.makedirs(install_dir, exist_ok=True)
            
            # Step 2: Chiudi l'applicazione se in esecuzione
            self.update_progress(20, "Chiusura applicazione esistente...")
            try:
                subprocess.run(['taskkill', '/F', '/IM', f'{APP_NAME}.exe'], 
                             capture_output=True, timeout=5)
            except:
                pass
            
            # Step 3: Copia l'eseguibile
            self.update_progress(40, "Copia file...")
            
            # Trova l'exe sorgente (nella stessa directory dell'installer o embedded)
            source_exe = self.find_source_exe()
            if source_exe:
                dest_exe = os.path.join(install_dir, f"{APP_NAME}.exe")
                shutil.copy2(source_exe, dest_exe)
            else:
                raise Exception("File eseguibile non trovato!")
            
            # Step 4: Copia altri file (logo, ecc.)
            self.update_progress(60, "Copia risorse...")
            for filename in ['logo.ico', 'logo.png']:
                source = self.find_resource(filename)
                if source and os.path.exists(source):
                    shutil.copy2(source, os.path.join(install_dir, filename))
            
            # Step 5: Crea shortcut sul desktop
            if self.create_desktop_shortcut.get():
                self.update_progress(70, "Creazione collegamento desktop...")
                self.create_shortcut(
                    os.path.join(install_dir, f"{APP_NAME}.exe"),
                    os.path.join(os.path.expanduser("~"), "Desktop", f"{APP_NAME}.lnk")
                )
            
            # Step 6: Crea voce nel menu start
            if self.create_start_menu.get():
                self.update_progress(85, "Creazione voce menu Start...")
                start_menu = os.path.join(
                    os.environ.get('APPDATA', ''),
                    'Microsoft', 'Windows', 'Start Menu', 'Programs'
                )
                if os.path.exists(start_menu):
                    self.create_shortcut(
                        os.path.join(install_dir, f"{APP_NAME}.exe"),
                        os.path.join(start_menu, f"{APP_NAME}.lnk")
                    )
            
            # Step 7: Completato
            self.update_progress(100, "Installazione completata!")
            
            # Vai alla pagina finale
            self.root.after(500, lambda: self.show_page(4))
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'installazione:\n{str(e)}")
            self.cancel_btn.config(state=tk.NORMAL)
    
    def update_progress(self, value, text):
        self.progress_bar['value'] = value
        self.progress_label.config(text=text)
        self.root.update()
    
    def find_source_exe(self):
        """Trova l'eseguibile sorgente (embedded nell'installer o nella stessa cartella)"""
        # Prima controlla se siamo in un bundle PyInstaller
        if getattr(sys, 'frozen', False):
            # Siamo in un exe - cerca l'app embedded o nella stessa directory
            
            # 1. Controlla nella cartella temporanea di PyInstaller (dati embedded)
            if hasattr(sys, '_MEIPASS'):
                exe_path = os.path.join(sys._MEIPASS, f"{APP_NAME}.exe")
                if os.path.exists(exe_path):
                    return exe_path
            
            # 2. Controlla nella directory dell'installer
            base_dir = os.path.dirname(sys.executable)
            exe_path = os.path.join(base_dir, f"{APP_NAME}.exe")
            if os.path.exists(exe_path) and exe_path != sys.executable:
                return exe_path
            
        else:
            # Siamo in sviluppo - cerca nella cartella dist
            base_dir = os.path.dirname(os.path.abspath(__file__))
            exe_path = os.path.join(base_dir, "dist", f"{APP_NAME}.exe")
            if os.path.exists(exe_path):
                return exe_path
        
        return None
    
    def find_resource(self, filename):
        """Trova un file risorsa (embedded o nella stessa cartella)"""
        if getattr(sys, 'frozen', False):
            # Prima controlla nei dati embedded
            if hasattr(sys, '_MEIPASS'):
                path = os.path.join(sys._MEIPASS, filename)
                if os.path.exists(path):
                    return path
            # Poi nella directory dell'exe
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            return path
        return None
    
    def create_shortcut(self, target, shortcut_path):
        """Crea un collegamento Windows usando PowerShell (nascosto)"""
        try:
            ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target}"
$Shortcut.WorkingDirectory = "{os.path.dirname(target)}"
$Shortcut.IconLocation = "{target}"
$Shortcut.Save()
'''
            # Usa CREATE_NO_WINDOW per nascondere completamente la finestra
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            subprocess.run(
                ['powershell', '-WindowStyle', 'Hidden', '-Command', ps_script], 
                capture_output=True, 
                timeout=10,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except:
            pass  # Ignora errori nella creazione shortcut
    
    def run(self):
        self.root.mainloop()


def main():
    # Verifica privilegi di amministratore
    if not is_admin():
        # Mostra messaggio e chiedi elevazione
        result = messagebox.askyesno(
            "Privilegi Amministratore Richiesti",
            f"L'installazione di {APP_NAME} richiede privilegi di amministratore.\n\n"
            "Vuoi continuare come amministratore?",
            icon='warning'
        )
        if result:
            if run_as_admin():
                sys.exit(0)  # Chiudi questa istanza, ne parte una elevata
            else:
                messagebox.showerror(
                    "Errore",
                    "Impossibile ottenere i privilegi di amministratore.\n"
                    "Prova a eseguire l'installer come amministratore."
                )
                sys.exit(1)
        else:
            sys.exit(0)
    
    app = InstallerApp()
    app.run()


if __name__ == "__main__":
    main()
