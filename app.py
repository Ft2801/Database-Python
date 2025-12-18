import os
import sys
import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QMessageBox, QApplication, QDialog, QLabel, QProgressBar, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon

from database import DatabaseManager
from updater import UpdateChecker, CURRENT_VERSION, check_for_updates, download_update, install_update
from config import StyleManager, ConfigManager
from ui_components import NavBar, SideBar, MainArea
from dialogs import (
    NewTableDialog, RecordDialog, AddColumnDialog, TutorialDialog,
    PasswordDialog, ChangePasswordDialog
)
from file_utils import get_files_dir


class UpdateWorker(QThread):
    """Worker thread per controllo e download aggiornamenti"""
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal()
    download_progress = pyqtSignal(int, int)
    download_complete = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, action="check", download_url=None):
        super().__init__()
        self.action = action
        self.download_url = download_url
    
    def run(self):
        try:
            if self.action == "check":
                update_info = check_for_updates()
                if update_info:
                    self.update_available.emit(update_info)
                else:
                    self.no_update.emit()
            elif self.action == "download" and self.download_url:
                def progress_callback(downloaded, total):
                    self.download_progress.emit(downloaded, total)
                
                path = download_update(self.download_url, progress_callback)
                if path:
                    self.download_complete.emit(path)
                else:
                    self.error.emit("Errore durante il download dell'aggiornamento")
        except Exception as e:
            self.error.emit(str(e))


class UpdateDialog(QDialog):
    """Dialogo per mostrare aggiornamenti disponibili e gestire il download"""
    
    def __init__(self, parent, update_info: dict):
        super().__init__(parent)
        self.update_info = update_info
        self.download_path = None
        self.worker = None
        
        self.setWindowTitle("Aggiornamento Disponibile")
        self.setFixedSize(450, 300)
        self.setModal(True)
        # Assicura che il dialogo sia in primo piano durante l'avvio
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Icona e titolo
        title = QLabel("🔄 Nuova versione disponibile!")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Informazioni versione
        version_info = QLabel(
            f"Versione attuale: {CURRENT_VERSION}\n"
            f"Nuova versione: {self.update_info.get('version', 'N/A')}"
        )
        version_info.setStyleSheet("font-size: 12px; color: #ffffff;")
        version_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_info)
        
        # Note di rilascio (se presenti)
        notes = self.update_info.get('release_notes', '')
        if notes:
            notes_label = QLabel("Note di rilascio:")
            notes_label.setStyleSheet("font-size: 11px; color: #aaaaaa; margin-top: 10px;")
            layout.addWidget(notes_label)
            
            notes_text = QLabel(notes[:200] + "..." if len(notes) > 200 else notes)
            notes_text.setWordWrap(True)
            notes_text.setStyleSheet("font-size: 10px; color: #cccccc; padding: 5px; background-color: rgba(30, 30, 50, 0.5); border-radius: 4px;")
            layout.addWidget(notes_text)
        
        layout.addStretch()
        
        # Barra di progresso (nascosta inizialmente)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - Scaricamento in corso...")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(30, 30, 50, 0.5);
                border: 1px solid rgba(59, 130, 241, 0.3);
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        layout.addWidget(self.status_label)
        
        # Pulsanti
        btn_layout = QHBoxLayout()
        
        self.btn_later = QPushButton("Più tardi")
        self.btn_later.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 0.5);
                color: white;
                border: 1px solid #666;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(120, 120, 120, 0.7);
            }
        """)
        self.btn_later.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_later)
        
        self.btn_update = QPushButton("Aggiorna ora")
        self.btn_update.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.btn_update.clicked.connect(self.start_download)
        btn_layout.addWidget(self.btn_update)
        
        layout.addLayout(btn_layout)
        
        # Stile del dialogo
        self.setStyleSheet("""
            UpdateDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e3a5f, stop:1 #000000);
            }
        """)
    
    def start_download(self):
        """Avvia il download dell'aggiornamento"""
        self.btn_update.setEnabled(False)
        self.btn_later.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_label.setText("Scaricamento in corso...")
        
        # Avvia il worker per il download
        self.worker = UpdateWorker("download", self.update_info['download_url'])
        self.worker.download_progress.connect(self.on_download_progress)
        self.worker.download_complete.connect(self.on_download_complete)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_download_progress(self, downloaded, total):
        """Aggiorna la barra di progresso"""
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.progress_bar.setFormat(f"{percent}% - {mb_downloaded:.1f}/{mb_total:.1f} MB")
    
    def on_download_complete(self, path):
        """Download completato, avvia l'installazione"""
        self.download_path = path
        self.status_label.setText("Download completato! Avvio installazione...")
        self.progress_bar.setValue(100)
        QApplication.processEvents()
        
        # Avvia l'installer
        success, message = install_update(path)
        if success:
            self.status_label.setText("Installer avviato. L'applicazione verrà chiusa...")
            self.status_label.setStyleSheet("font-size: 11px; color: #4ade80;")
            QApplication.processEvents()
            # Chiudi l'applicazione per permettere l'aggiornamento
            import time
            time.sleep(2)
            QApplication.quit()
        else:
            self.on_error(f"Impossibile avviare l'installer: {message}")
    
    def on_error(self, error_msg):
        """Gestisce gli errori"""
        self.status_label.setText(f"Errore: {error_msg}")
        self.status_label.setStyleSheet("font-size: 11px; color: #ef4444;")
        self.btn_later.setEnabled(True)
        self.btn_update.setEnabled(True)
        self.progress_bar.hide()


class SplashScreen(QWidget):
    """Schermata di avvio con barra di caricamento"""
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(400, 250)
        
        # Centra la finestra sullo schermo
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            screen = primary_screen.geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Logo/Titolo
        title = QLabel("DatabasePro")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
        """)
        layout.addWidget(title)
        
        # Sottotitolo con versione
        subtitle = QLabel(f"Gestione Database Avanzata - v{CURRENT_VERSION}")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(subtitle)
        
        layout.addStretch()
        
        # Barra di avanzamento
        self.progress = QProgressBar()
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: rgba(30, 30, 50, 0.5);
                border: 1px solid rgba(59, 130, 241, 0.3);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress)
        
        # Stato caricamento
        self.status_label = QLabel("Inizializzazione...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        layout.addWidget(self.status_label)
        
        # Stile del widget (gradiente come l'app)
        self.setStyleSheet("""
            SplashScreen {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e3a5f, stop:1 #000000);
                border: 1px solid rgba(59, 130, 241, 0.5);
                border-radius: 12px;
            }
        """)
    
    def set_progress(self, value: int, status: str):
        """Aggiorna la barra e il testo di stato"""
        self.progress.setValue(value)
        self.status_label.setText(status)
        QApplication.processEvents()


def get_app_path():
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DB_NAME = "database_avanzato.db"
CONFIG_FILE = "app_config.json"


class ModernDBApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.app_path = get_app_path()
        self.config_path = os.path.join(self.app_path, CONFIG_FILE)

        # Determine data paths. For frozen (packaged) builds we want to
        # place database, auth and key in a persistent AppData location so:
        # 1. User can delete/replace EXE without losing data
        # 2. Database persists across app updates
        import sys as _sys
        if getattr(_sys, 'frozen', False):
            # Build EXE: usa sempre ProgramData per persistenza dei dati
            program_data = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
            data_dir = os.path.join(program_data, 'DatabasePro')
            try:
                os.makedirs(data_dir, exist_ok=True)
            except Exception:
                # Se non riesce a creare in ProgramData, usa AppData locale
                local_app_data = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
                data_dir = os.path.join(local_app_data, 'DatabasePro')
                os.makedirs(data_dir, exist_ok=True)
        else:
            # Sviluppo: usa la directory dell'app
            data_dir = self.app_path

        # Database, auth, and key are all in the persistent data directory
        self.db_path = os.path.join(data_dir, DB_NAME)
        self.auth_path = os.path.join(data_dir, 'auth.json')
        key_path = os.path.join(data_dir, 'db_key.key')
        
        # Debug: stampa il percorso per verifica (solo in frozen mode)
        if getattr(_sys, 'frozen', False):
            print(f"[DatabasePro] Data directory: {data_dir}")

        # Ensure an application-local key file is used for DB encryption when available
        self.db_manager = DatabaseManager(self.db_path, key_path=key_path)
        self.config_manager = ConfigManager(self.config_path)
        self.style_manager = StyleManager()
        
        # Default to the dark theme
        theme: str = self.config_manager.get("theme", "Elegant Dark") or "Elegant Dark"
        self.style_manager.set_theme(theme)
        # Apply an appropriate palette for the selected theme
        try:
            self.set_palette_for_theme(theme)
        except Exception:
            pass
        
        self.init_ui()
        self.setWindowTitle("Gestione Database")
        
        # Imposta l'icona dell'applicazione
        logo_path = os.path.join(self.app_path, "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
        
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setMinimumSize(1200, 700)
        
        self.apply_stylesheet()
        self.setup_shortcuts()
    
    def _show_status(self, message: str):
        """Helper per mostrare messaggi nella status bar"""
        status_bar = self.statusBar()
        if status_bar:
            status_bar.showMessage(message)
    
    def setup_shortcuts(self):
        """Configura le scorciatoie da tastiera"""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # Ctrl+Z per Undo
        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(self.perform_undo)
        
        # Ctrl+Shift+Z per Redo
        redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
        redo_shortcut.activated.connect(self.perform_redo)
    
    def init_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.navbar = NavBar(self.style_manager)
        # Theme is now fixed to dark gradient - no theme switching
        self.navbar.backup_requested.connect(self.backup_database)
        self.navbar.tutorial_requested.connect(self.show_tutorial)
        # connect password change request from the navbar
        try:
            self.navbar.password_change_requested.connect(self.show_change_password_dialog)
        except Exception:
            pass
        main_layout.addWidget(self.navbar)
        
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        self.sidebar = SideBar(self.style_manager, self.db_manager)
        self.sidebar.table_selected.connect(self.load_table)
        self.sidebar.new_table.connect(self.show_new_table_dialog)
        self.sidebar.delete_table.connect(self.delete_table)
        content_layout.addWidget(self.sidebar)
        
        self.main_area = MainArea(self.style_manager, self.db_manager)
        self.main_area.new_btn.clicked.connect(self.show_add_record_dialog)
        self.main_area.edit_btn.clicked.connect(self.show_edit_record_dialog)
        self.main_area.del_btn.clicked.connect(self.delete_record)
        self.main_area.col_btn.clicked.connect(self.show_add_column_dialog)
        self.main_area.search_input.returnPressed.connect(self.search_records)
        content_layout.addWidget(self.main_area)
        
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)
        # Apply theme styles for components that need per-widget styling
        try:
            self.main_area.apply_theme_styles()
        except Exception:
            pass
        
        self._show_status("Pronto")
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        self.sidebar.load_tables()
    
    def apply_stylesheet(self):
        self.setStyleSheet("")

    def set_palette_for_theme(self, theme: str):
        """Imposta la palette dell'applicazione in base al nome del tema."""
        from PyQt6.QtGui import QPalette, QColor
        from PyQt6.QtWidgets import QApplication

        p = QPalette()
        if theme == 'Clean White':
            p.setColor(QPalette.ColorRole.Window, QColor('#ffffff'))
            p.setColor(QPalette.ColorRole.WindowText, QColor('#000000'))
            p.setColor(QPalette.ColorRole.Base, QColor('#ffffff'))
            p.setColor(QPalette.ColorRole.AlternateBase, QColor('#f9fafb'))
            p.setColor(QPalette.ColorRole.ToolTipBase, QColor('#ffffff'))
            p.setColor(QPalette.ColorRole.ToolTipText, QColor('#000000'))
            p.setColor(QPalette.ColorRole.Text, QColor('#000000'))
            p.setColor(QPalette.ColorRole.Button, QColor('#f3f4f6'))
            p.setColor(QPalette.ColorRole.ButtonText, QColor('#000000'))
            p.setColor(QPalette.ColorRole.BrightText, QColor('#ff0000'))
            p.setColor(QPalette.ColorRole.Highlight, QColor('#3b82f6'))
            p.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
        elif theme == 'Elegant Dark':
            p.setColor(QPalette.ColorRole.Window, QColor('#0f1419'))
            p.setColor(QPalette.ColorRole.WindowText, QColor('#e0e0e0'))
            p.setColor(QPalette.ColorRole.Base, QColor('#1a1f2e'))
            p.setColor(QPalette.ColorRole.AlternateBase, QColor('#0d0f14'))
            p.setColor(QPalette.ColorRole.ToolTipBase, QColor('#1a1f2e'))
            p.setColor(QPalette.ColorRole.ToolTipText, QColor('#e0e0e0'))
            p.setColor(QPalette.ColorRole.Text, QColor('#e0e0e0'))
            p.setColor(QPalette.ColorRole.Button, QColor('#1a1f2e'))
            p.setColor(QPalette.ColorRole.ButtonText, QColor('#e0e0e0'))
            p.setColor(QPalette.ColorRole.BrightText, QColor('#ff0000'))
            p.setColor(QPalette.ColorRole.Highlight, QColor('#6366f1'))
            p.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
        else:
            # fallback: leave default palette
            return

        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            app.setPalette(p)
    
    def show_tutorial(self):
        dialog = TutorialDialog(self, self.style_manager)
        dialog.exec()

    def show_change_password_dialog(self):
        dialog = ChangePasswordDialog(self, self.auth_path)
        dialog.exec()
    
    def load_table(self, table_name: str):
        self.main_area.load_table(table_name)
        self._show_status(f"Tabella: {table_name}")
    
    def show_new_table_dialog(self):
        dialog = NewTableDialog(self, self.db_manager, self.style_manager)
        if dialog.exec():
            self.sidebar.load_tables()
            self._show_status("Tabella creata con successo")
    
    def delete_table(self):
        table = self.sidebar.get_selected_table()
        if not table:
            return
        
        reply = QMessageBox.question(self, "Conferma", f"Eliminare la tabella '{table}'?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Before dropping, delete any files associated with FILE columns
            try:
                from file_utils import get_files_dir, parse_multi_file_value
                cols = self.db_manager.get_columns(table)
                file_cols = []
                for col in cols:
                    col_name = col[1]
                    spec = self.db_manager.get_special_type(table, col_name)
                    if spec and spec[0] == 'FILE':
                        file_cols.append(col_name)
                
                if file_cols:
                    records = self.db_manager.get_records(table)
                    files_dir = get_files_dir()
                    for record in records:
                        for col in cols:
                            col_name = col[1]
                            if col_name in file_cols:
                                col_idx = [c[1] for c in cols].index(col_name)
                                db_value = record[col_idx]
                                if db_value:
                                    try:
                                        # Parse multi-file format and delete all files
                                        files = parse_multi_file_value(str(db_value))
                                        for _, encrypted_filename in files:
                                            if encrypted_filename:
                                                file_path = os.path.join(files_dir, encrypted_filename)
                                                if os.path.exists(file_path):
                                                    os.remove(file_path)
                                    except Exception:
                                        pass
            except Exception:
                pass
            
            if self.db_manager.drop_table(table):
                self.sidebar.load_tables()
                self.main_area.current_table = None
                self.main_area.table_widget.setRowCount(0)
                self.main_area.table_widget.setColumnCount(0)
                self.main_area.title_label.setText("Seleziona una tabella")
                self._show_status("Tabella eliminata")
    
    def show_add_record_dialog(self):
        if not self.main_area.current_table:
            return
        dialog = RecordDialog(self, self.db_manager, self.style_manager, self.main_area.current_table)
        if dialog.exec():
            self.main_area.refresh_table_data()
            self._show_status("Record aggiunto")
    
    def show_edit_record_dialog(self):
        if not self.main_area.current_table:
            return
        
        selected_rows = self.main_area.table_widget.selectedIndexes()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        from PyQt6.QtCore import Qt
        item = self.main_area.table_widget.item(row, 0)
        if not item:
            return
        record_id = item.data(Qt.ItemDataRole.UserRole)
        
        if not self.main_area.current_table:
            return
        columns = self.db_manager.get_columns(self.main_area.current_table)
        records = self.db_manager.get_records(self.main_area.current_table, "id=?", (record_id,))
        
        if records:
            dialog = RecordDialog(self, self.db_manager, self.style_manager, 
                                self.main_area.current_table, records[0])
            if dialog.exec():
                self.main_area.refresh_table_data()
                self._show_status("Record aggiornato")
    
    def delete_record(self):
        selected_rows = self.main_area.table_widget.selectedIndexes()
        if not selected_rows:
            return
        
        reply = QMessageBox.question(self, "Conferma", "Eliminare il record?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            row = selected_rows[0].row()
            from PyQt6.QtCore import Qt
            item = self.main_area.table_widget.item(row, 0)
            if not item:
                return
            record_id = item.data(Qt.ItemDataRole.UserRole)
            
            current_table = self.main_area.current_table
            if not current_table:
                return

            # Before deleting the DB row, remove any copied files for FILE columns
            try:
                from file_utils import parse_multi_file_value
                old_record = self.db_manager.get_records(current_table, "id=?", (record_id,))
                if old_record:
                    cols = self.db_manager.get_columns(current_table)
                    for idx, col in enumerate(cols):
                        col_name = col[1]
                        spec = self.db_manager.get_special_type(current_table, col_name)
                        if spec and spec[0] == 'FILE':
                            db_value = old_record[0][idx]
                            if db_value:
                                try:
                                    # Parse multi-file format and delete all files
                                    files = parse_multi_file_value(str(db_value))
                                    for _, encrypted_filename in files:
                                        if encrypted_filename:
                                            try:
                                                files_dir = get_files_dir()
                                                path_to_remove = os.path.join(files_dir, encrypted_filename)
                                            except Exception:
                                                files_dir = os.path.join(self.app_path, 'files')
                                                path_to_remove = os.path.join(files_dir, encrypted_filename)
                                            if os.path.exists(path_to_remove):
                                                os.remove(path_to_remove)
                                except Exception:
                                    pass
            except Exception:
                pass

            if current_table and self.db_manager.delete_record(current_table, record_id):
                self.main_area.refresh_table_data()
                self._show_status("Record eliminato")
    
    def search_records(self):
        if not self.main_area.current_table:
            return
        
        search_text = self.main_area.search_input.text()
        if not search_text:
            self.main_area.refresh_table_data()
            return
        
        columns = [col[1] for col in self.db_manager.get_columns(self.main_area.current_table)]
        where_clause = " OR ".join([f'"{col}" LIKE ?' for col in columns])
        params = tuple([f"%{search_text}%" for _ in columns])
        
        self.main_area.table_widget.setRowCount(0)
        records = self.db_manager.get_records(self.main_area.current_table, where_clause, params)
        
        from PyQt6.QtWidgets import QTableWidgetItem
        from PyQt6.QtCore import Qt
        
        self.main_area.table_widget.setRowCount(len(records))
        
        for row_idx, record in enumerate(records):
            for col_idx, value in enumerate(record):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setData(Qt.ItemDataRole.UserRole, record[0])
                self.main_area.table_widget.setItem(row_idx, col_idx, item)
    
    def show_add_column_dialog(self):
        if not self.main_area.current_table:
            return
        dialog = AddColumnDialog(self, self.db_manager, self.style_manager, self.main_area.current_table)
        if dialog.exec():
            self.main_area.refresh_table_data()
            self._show_status("Colonna aggiunta")
    
    def backup_database(self):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{ts}.db"
        backup_path = os.path.join(self.app_path, backup_filename)
        
        if self.db_manager.backup_db(backup_path):
            QMessageBox.information(self, "Backup", f"Database sottoposto a backup come: {backup_filename}")
            self._show_status("Backup completato")
        else:
            QMessageBox.warning(self, "Errore Backup", "Errore nel backup del database")
    
    def perform_undo(self):
        """Esegue l'operazione di undo"""
        if not self.db_manager.can_undo():
            self._show_status("Nessuna operazione da annullare")
            return
        
        success, message = self.db_manager.undo()
        if success:
            self.main_area.refresh_table_data()
            self._show_status(message)
        else:
            self._show_status(message)
    
    def perform_redo(self):
        """Esegue l'operazione di redo"""
        if not self.db_manager.can_redo():
            self._show_status("Nessuna operazione da ripristinare")
            return
        
        success, message = self.db_manager.redo()
        if success:
            self.main_area.refresh_table_data()
            self._show_status(message)
        else:
            self._show_status(message)

    def closeEvent(self, a0):
        """Ensure DB is committed/encrypted on application close."""
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                try:
                    # try to commit any pending transactions
                    conn = getattr(self.db_manager, 'conn', None)
                    if conn:
                        try:
                            conn.commit()
                        except Exception:
                            pass
                except Exception:
                    pass

                try:
                    self.db_manager.close()
                except Exception as e:
                    print(f"Error closing database: {e}")
        except Exception:
            pass

        try:
            # allow normal close to proceed
            super().closeEvent(a0)
        except Exception:
            if a0:
                a0.accept()


if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    # Use a predictable Fusion style
    try:
        app.setStyle('Fusion')
    except Exception:
        pass

    # Apply dark palette with blue-to-black gradient theme (white text)
    try:
        from PyQt6.QtGui import QPalette, QColor
        p = QPalette()
        # Dark base colors for gradient theme
        p.setColor(QPalette.ColorRole.Window, QColor('#0a0a14'))
        p.setColor(QPalette.ColorRole.WindowText, QColor('#ffffff'))
        p.setColor(QPalette.ColorRole.Base, QColor('#0a0a14'))
        p.setColor(QPalette.ColorRole.AlternateBase, QColor('#101020'))
        p.setColor(QPalette.ColorRole.ToolTipBase, QColor('#1a1a2e'))
        p.setColor(QPalette.ColorRole.ToolTipText, QColor('#ffffff'))
        p.setColor(QPalette.ColorRole.Text, QColor('#ffffff'))
        p.setColor(QPalette.ColorRole.Button, QColor('#1a1a2e'))
        p.setColor(QPalette.ColorRole.ButtonText, QColor('#ffffff'))
        p.setColor(QPalette.ColorRole.BrightText, QColor('#ff6b6b'))
        p.setColor(QPalette.ColorRole.Highlight, QColor('#3b82f6'))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
        p.setColor(QPalette.ColorRole.PlaceholderText, QColor('#888888'))
        app.setPalette(p)
    except Exception:
        pass

    # Set global stylesheet with gradient background and white text
    app.setStyleSheet("""
        QMainWindow {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1e3a5f, stop:1 #000000);
        }
        QWidget {
            color: #ffffff;
        }
        QFrame {
            background-color: transparent;
        }
        QFrame#sidebarFrame, QFrame#mainAreaFrame {
            background-color: rgba(10, 10, 20, 0.25);
            border-radius: 8px;
            border: 1px solid rgba(59, 130, 241, 0.3);
        }
        QLabel {
            background-color: transparent;
            color: #ffffff;
        }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: rgba(30, 30, 50, 0.25);
            color: #ffffff;
            border: 1px solid #3b82f6;
            border-radius: 4px;
            padding: 4px;
        }
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 2px solid #60a5fa;
        }
        QPushButton {
            background-color: rgba(30, 58, 95, 0.5);
            color: #ffffff;
            border: 1px solid rgba(59, 130, 241, 0.5);
            border-radius: 6px;
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: rgba(42, 74, 112, 0.7);
        }
        QPushButton:pressed {
            background-color: rgba(15, 42, 74, 0.8);
        }
        QTableWidget {
            background-color: rgba(10, 10, 20, 0.25);
            color: #ffffff;
            gridline-color: rgba(59, 130, 241, 0.5);
            selection-background-color: #3b82f6;
            border: 1px solid rgba(59, 130, 241, 0.3);
            border-radius: 4px;
        }
        QTableWidget::item {
            color: #ffffff;
        }
        QHeaderView::section {
            background-color: rgba(30, 58, 95, 0.5);
            color: #ffffff;
            border: 1px solid rgba(59, 130, 241, 0.3);
            padding: 4px;
        }
        QListWidget {
            background-color: rgba(10, 10, 20, 0.25);
            color: #ffffff;
            border: 1px solid rgba(59, 130, 241, 0.3);
            border-radius: 4px;
        }
        QListWidget::item {
            color: #ffffff;
        }
        QListWidget::item:selected {
            background-color: #3b82f6;
        }
        QMenuBar {
            background-color: rgba(10, 10, 20, 0.25);
            color: #ffffff;
        }
        QMenuBar::item:selected {
            background-color: rgba(30, 58, 95, 0.5);
        }
        QMenu {
            background-color: rgba(26, 26, 46, 0.9);
            color: #ffffff;
            border: 1px solid rgba(59, 130, 241, 0.3);
        }
        QMenu::item:selected {
            background-color: #3b82f6;
        }
        QScrollBar:vertical {
            background-color: rgba(10, 10, 20, 0.25);
            width: 12px;
        }
        QScrollBar::handle:vertical {
            background-color: rgba(59, 130, 241, 0.5);
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar:horizontal {
            background-color: rgba(10, 10, 20, 0.25);
            height: 12px;
        }
        QScrollBar::handle:horizontal {
            background-color: rgba(59, 130, 241, 0.5);
            border-radius: 6px;
            min-width: 20px;
        }
        QScrollBar::add-line, QScrollBar::sub-line {
            background: transparent;
            height: 0px;
            width: 0px;
        }
        QScrollBar::add-page, QScrollBar::sub-page {
            background: transparent;
        }
        QDialog {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1e3a5f, stop:1 #000000);
        }
        QScrollArea {
            background-color: transparent;
            border: none;
        }
        QScrollArea > QWidget > QWidget {
            background-color: transparent;
        }
        QGroupBox {
            background-color: rgba(10, 10, 20, 0.25);
            color: #ffffff;
            border: 1px solid rgba(59, 130, 241, 0.3);
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QGroupBox::title {
            color: #ffffff;
        }
        QCheckBox {
            color: #ffffff;
        }
        QRadioButton {
            color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid rgba(59, 130, 241, 0.3);
            background-color: rgba(10, 10, 20, 0.25);
        }
        QTabBar::tab {
            background-color: rgba(26, 26, 46, 0.25);
            color: #ffffff;
            border: 1px solid rgba(59, 130, 241, 0.3);
            padding: 8px 16px;
        }
        QTabBar::tab:selected {
            background-color: #3b82f6;
        }
    """)

    # Mostra splash screen
    splash = SplashScreen()
    splash.show()
    QApplication.processEvents()
    
    import time
    
    # Step 1: Inizializzazione
    splash.set_progress(5, "Inizializzazione ambiente...")
    time.sleep(0.1)
    
    # Step 2: Controllo aggiornamenti
    splash.set_progress(15, "Controllo aggiornamenti...")
    QApplication.processEvents()
    update_info = None
    try:
        update_info = check_for_updates()
        if update_info:
            splash.set_progress(20, f"Nuova versione disponibile: {update_info.get('version', '')}")
        else:
            splash.set_progress(20, "Applicazione aggiornata")
    except Exception as e:
        print(f"[Updater] Errore controllo aggiornamenti: {e}")
        splash.set_progress(20, "Controllo aggiornamenti fallito")
    time.sleep(0.1)
    
    # Step 3: Caricamento moduli
    splash.set_progress(35, "Caricamento moduli...")
    import auth as auth_mod
    import sys as _sys
    time.sleep(0.1)
    
    # Step 4: Configurazione percorsi
    splash.set_progress(50, "Configurazione percorsi dati...")
    app_path = os.path.dirname(os.path.abspath(__file__))
    time.sleep(0.1)
    
    # Step 5: Preparazione autenticazione
    splash.set_progress(70, "Preparazione autenticazione...")
    if getattr(_sys, 'frozen', False):
        try:
            from file_utils import get_files_dir as _get_files_dir
            _data_dir = os.path.dirname(_get_files_dir())
            os.makedirs(_data_dir, exist_ok=True)
            auth_path = os.path.join(_data_dir, 'auth.json')
            auth_mod.ensure_password_file(auth_path, default_password='Admin')
        except Exception:
            auth_path = os.path.join(app_path, 'auth.json')
            auth_mod.ensure_password_file(auth_path, default_password='Admin')
    else:
        auth_path = os.path.join(app_path, 'auth.json')
        auth_mod.ensure_password_file(auth_path, default_password='Admin')
    time.sleep(0.1)
    
    # Step 6: Caricamento database
    splash.set_progress(90, "Caricamento database...")
    time.sleep(0.1)
    
    # Step 7: Completamento
    splash.set_progress(100, "Pronto!")
    time.sleep(0.1)
    
    # Se c'è un aggiornamento disponibile, mostra il dialogo prima di chiudere lo splash
    # per evitare un "buco" visivo tra le due finestre
    if update_info:
        # Nascondi lo splash invece di chiuderlo subito
        splash.hide()
        
        update_dialog = UpdateDialog(None, update_info)
        # Applica lo stile al dialogo
        update_dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e3a5f, stop:1 #000000);
                border: 1px solid #3b82f6;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        # Se l'utente sceglie di aggiornare, il dialogo chiuderà l'app
        # Se sceglie "più tardi", continua normalmente
        update_dialog.exec()
        
    # Chiudi definitivamente lo splash
    splash.close()

    # Authentication setup
    try:
        pwd_dialog = PasswordDialog(None, auth_path)
        # If the user cancels or fails to authenticate, exit
        if pwd_dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
    except Exception:
        # If anything goes wrong with auth, block access as a safe default
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Errore", "Errore nel sistema di autenticazione. Uscita.")
        except Exception:
            pass
        sys.exit(1)

    window = ModernDBApp()
    # Ensure DB is closed properly even if exit happens outside Qt main loop
    try:
        import atexit
        atexit.register(lambda: getattr(window, 'db_manager', None) and window.db_manager.close())
    except Exception:
        pass
    
    window.show()
    
    sys.exit(app.exec())

