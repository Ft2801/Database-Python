from typing import Tuple
import os
import uuid
from file_utils import (
    get_files_dir, encrypt_file, parse_file_value, format_file_value, 
    delete_encrypted_file, parse_multi_file_value, format_multi_file_value,
    get_display_names_from_multi_file
)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QListWidget, QListWidgetItem, QFrame, QScrollArea, QWidget, QMessageBox,
    QFileDialog, QDateEdit, QDoubleSpinBox, QApplication, QPlainTextEdit
)
from PyQt6.QtCore import QDate, Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon

from validators import InputValidator
from config import StyleManager
from database import DatabaseManager


class MultiLineTextEdit(QPlainTextEdit):
    """Custom text edit that saves on Enter and allows newlines with Shift+Enter."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(100)
        self.setMinimumHeight(60)
    
    def keyPressEvent(self, event):
        # Shift+Enter inserts a newline
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Insert newline
                super().keyPressEvent(event)
            else:
                # Trigger save (handled by parent dialog)
                # Find parent RecordDialog and save
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'save_btn_ref') and hasattr(parent, 'save_record'):
                        if parent.save_btn_ref and parent.save_btn_ref.isEnabled():
                            parent.save_record()
                        return
                    parent = parent.parent()
        else:
            super().keyPressEvent(event)


class TutorialDialog(QDialog):
    def __init__(self, parent, style_manager: StyleManager):
        super().__init__(parent)
        self.style_manager = style_manager
        
        self.setWindowTitle("Tutorial - Guida all'Applicazione")
        self.center_on_screen()
        self.init_ui()
    
    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        width = int(screen_geometry.width() * 0.6)
        height = int(screen_geometry.height() * 0.75)
        
        self.setGeometry(0, 0, width, height)
        
        x = (screen_geometry.width() - width) // 2
        y = (screen_geometry.height() - height) // 2
        self.move(x, y)
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Guida all'Applicazione")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        main_layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        tutorial_sections = [
            {
                "title": "Gestione Tabelle",
                "content": [
                    "• Nella barra laterale sinistra visualizzi tutte le tabelle del database",
                    "• Clicca su una tabella per visualizzarne i dati",
                    "• Usa il pulsante 'Nuova Tabella' per creare una nuova tabella",
                    "• Seleziona una tabella e clicca 'Elimina Tabella' per eliminarla"
                ]
            },
            {
                "title": "Visualizzazione Dati",
                "content": [
                    "• Una volta selezionata una tabella, i dati vengono visualizzati nella griglia centrale",
                    "• La colonna ID è nascosta ma viene usata internamente",
                    "• Doppio clic su una cella per aprire l'editor dedicato e modificare il valore",
                    "• La ricerca in alto a destra consente di filtrare i dati"
                ]
            },
            {
                "title": "Gestione Record",
                "content": [
                    "• Nuovo Record: Aggiunge un nuovo record alla tabella",
                    "• Modifica: Modifica il record selezionato",
                    "• Elimina: Elimina il record selezionato",
                    "• Doppio clic su una cella per modificarla direttamente"
                ]
            },
            {
                "title": "Gestione Colonne",
                "content": [
                    "• Aggiungi Colonna: Aggiunge una nuova colonna alla tabella",
                    "• Doppio clic sull'intestazione: Rinomina una colonna esistente",
                    "• Tipi disponibili: TESTO, DATA, FILE",
                    "• Le colonne FILE permettono di allegare più file a ciascun record"
                ]
            },
            {
                "title": "Scorciatoie da Tastiera",
                "content": [
                    "• Invio: Salva la modifica nella cella o nel campo",
                    "• Shift+Invio: Vai a capo nelle caselle di testo multi-riga",
                    "• Ctrl+Z: Annulla l'ultima operazione (max 3)",
                    "• Ctrl+Shift+Z: Ripristina l'operazione annullata",
                    "• Doppio clic: Apre l'editor per celle o rinomina colonne"
                ]
            },
            {
                "title": "Undo/Redo",
                "content": [
                    "• Il sistema tiene traccia delle ultime 3 operazioni",
                    "• Supporta: inserimento, modifica ed eliminazione record",
                    "• Ctrl+Z annulla l'ultima operazione",
                    "• Ctrl+Shift+Z ripristina l'operazione annullata",
                    "• Il feedback appare nella barra di stato"
                ]
            },
            {
                "title": "Sicurezza",
                "content": [
                    "• Il database è protetto con crittografia AES-128",
                    "• Cambia Password: Modifica la password di accesso all'applicazione",
                    "• Backup: Crea una copia di sicurezza del database"
                ]
            },
            {
                "title": "Aggiornamenti",
                "content": [
                    "• L'applicazione verifica automaticamente la presenza di aggiornamenti all'avvio",
                    "• Se disponibile una nuova versione, verrà proposto il download e l'installazione",
                    "• Gli aggiornamenti preservano tutti i dati esistenti"
                ]
            },
            {
                "title": "Ricerca",
                "content": [
                    "• Usa il campo di ricerca in alto a destra per filtrare i record",
                    "• La ricerca è case-insensitive e funziona su tutti i campi"
                ]
            }
        ]
        
        for section in tutorial_sections:
            section_title = QLabel(section["title"])
            section_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            scroll_layout.addWidget(section_title)
            
            for line in section["content"]:
                line_label = QLabel(line)
                line_label.setFont(QFont("Segoe UI", 10))
                # default colors
                scroll_layout.addWidget(line_label)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)
        
        self.setLayout(main_layout)


def center_dialog(dialog, width_percent=0.5, height_percent=0.75):
    screen = QApplication.primaryScreen()
    screen_geometry = screen.geometry()
    width = int(screen_geometry.width() * width_percent)
    height = int(screen_geometry.height() * height_percent)
    
    dialog.setGeometry(0, 0, width, height)
    
    x = (screen_geometry.width() - width) // 2
    y = (screen_geometry.height() - height) // 2
    dialog.move(x, y)


class NewTableDialog(QDialog):
    def __init__(self, parent, db_manager: DatabaseManager, style_manager: StyleManager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.style_manager = style_manager
        self.columns = []
        
        self.setWindowTitle("Crea Nuova Tabella")
        center_dialog(self, 0.45, 0.8)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("Crea Nuova Tabella")
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        title.setFont(title_font)
        layout.addWidget(title)
        
        name_label = QLabel("Nome Tabella:")
        name_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome tabella...")
        layout.addWidget(self.name_input)
        
        columns_label = QLabel("Colonne:")
        columns_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(columns_label)
        
        self.columns_list = QListWidget()
        layout.addWidget(self.columns_list)
        
        add_col_group = QFrame()
        add_col_layout = QVBoxLayout()
        
        add_col_title = QLabel("Aggiungi Colonna")
        add_col_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        add_col_layout.addWidget(add_col_title)
        
        input_layout = QHBoxLayout()
        
        col_name_label = QLabel("Nome:")
        self.col_name_input = QLineEdit()
        self.col_name_input.setPlaceholderText("Nome colonna...")
        self.col_name_input.setMaximumWidth(150)
        input_layout.addWidget(col_name_label)
        input_layout.addWidget(self.col_name_input)
        
        type_label = QLabel("Tipo:")
        self.col_type_combo = QComboBox()
        self.col_type_combo.addItems(["TESTO", "DATA", "FILE"])
        self.col_type_combo.setMaximumWidth(120)
        input_layout.addWidget(type_label)
        input_layout.addWidget(self.col_type_combo)
        
        add_col_layout.addLayout(input_layout)
        
        add_btn = QPushButton("Aggiungi Colonna")
        add_btn.clicked.connect(self.add_column)
        add_col_layout.addWidget(add_btn)
        
        add_col_group.setLayout(add_col_layout)
        layout.addWidget(add_col_group)
        
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("CREA TABELLA")
        create_btn.clicked.connect(self.create_table)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def add_column(self):
        col_name = self.col_name_input.text().strip()
        col_type = self.col_type_combo.currentText()
        
        if not col_name:
            return
        
        # Controllo duplicati: verifica se esiste già una colonna con lo stesso nome
        existing_names = [col['name'].lower() for col in self.columns]
        if col_name.lower() in existing_names:
            QMessageBox.warning(self, "Errore", f"Esiste già una colonna con il nome '{col_name}'.")
            return
        
        sql_type = "TEXT"
        special = ""
        
        if col_type == "FILE":
            sql_type = "TEXT"
            special = "FILE"
        elif col_type == "DATA":
            special = "DATE"
        
        self.columns.append({
            'name': col_name,
            'sql_type': sql_type,
            'special': special if special else None,
            'extra': ''
        })
        
        self.col_name_input.clear()
        self.update_columns_list()
    
    def update_columns_list(self):
        self.columns_list.clear()
        for col in self.columns:
            info = f"{col['name']} ({col['sql_type']})"
            if col['special']:
                info += f" [{col['special']}]"
            self.columns_list.addItem(info)
    
    def create_table(self):
        table_name = self.name_input.text().strip()
        
        if not table_name or not self.columns:
            QMessageBox.warning(self, "Errore", "Nome tabella e almeno una colonna necessari.")
            return
        
        if self.db_manager.create_table(table_name, self.columns):
            QMessageBox.information(self, "Successo", f"Tabella '{table_name}' creata!")
            self.accept()
        else:
            QMessageBox.warning(self, "Errore", "Errore nella creazione della tabella.")


class RecordDialog(QDialog):
    def __init__(self, parent, db_manager: DatabaseManager, style_manager: StyleManager, 
                 table_name: str, record_data: Tuple = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.style_manager = style_manager
        self.table_name = table_name
        self.record_data = record_data
        self.record_id = record_data[0] if record_data else None
        self.widgets = {}
        
        self.setWindowTitle("Aggiungi Nuovo Record" if not record_data else "Modifica Record")
        center_dialog(self, 0.4, 0.75)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        title_text = "Aggiungi Nuovo Record" if not self.record_data else "Modifica Record"
        title = QLabel(title_text)
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        title.setFont(title_font)
        layout.addWidget(title)
        
        self.validation_label = QLabel("")
        layout.addWidget(self.validation_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        form_layout = QVBoxLayout()
        
        columns = self.db_manager.get_columns(self.table_name)
        
        for col_idx, col in enumerate(columns):
            col_name = col[1]
            is_pk = col[5]
            
            if is_pk:
                continue
            
            value = self.record_data[col_idx] if self.record_data else None
            
            label = QLabel(col_name)
            label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            form_layout.addWidget(label)
            
            spec_info = self.db_manager.get_special_type(self.table_name, col_name)
            spec_type = spec_info[0] if spec_info else None
            
            if spec_type == "FILE":
                # Multi-file picker: encrypt and copy selected files into app's files/ folder
                file_frame = QFrame()
                file_main_layout = QVBoxLayout()
                file_main_layout.setContentsMargins(0, 0, 0, 0)

                # List widget to show selected files
                file_list = QListWidget()
                file_list.setMaximumHeight(100)
                file_main_layout.addWidget(file_list)

                # Data structure to hold list of files: [(original_name, encrypted_filename), ...]
                existing_files = parse_multi_file_value(str(value)) if value else []
                file_data = {"files": existing_files.copy()}

                def update_file_list(lst, data):
                    lst.clear()
                    for orig, _ in data["files"]:
                        lst.addItem(orig)

                update_file_list(file_list, file_data)

                def make_add_file(lst, data):
                    def add_file():
                        src_paths, _ = QFileDialog.getOpenFileNames(self, "Seleziona File", "", "Tutti i file (*.*)")
                        for src_path in src_paths:
                            if src_path:
                                try:
                                    files_dir = get_files_dir()
                                    original_name = os.path.basename(src_path)
                                    # Create encrypted filename with .enc extension
                                    encrypted_name = f"{uuid.uuid4().hex}.enc"
                                    dest_path = os.path.join(files_dir, encrypted_name)
                                    # Encrypt and save the file
                                    if encrypt_file(src_path, dest_path):
                                        data["files"].append((original_name, encrypted_name))
                                except Exception:
                                    pass
                        update_file_list(lst, data)
                        self.validate_form()
                    return add_file

                def make_remove_selected(lst, data):
                    def remove_selected():
                        current_row = lst.currentRow()
                        if current_row >= 0 and current_row < len(data["files"]):
                            # Delete the physical file
                            _, encrypted_filename = data["files"][current_row]
                            if encrypted_filename:
                                delete_encrypted_file(encrypted_filename)
                            data["files"].pop(current_row)
                            update_file_list(lst, data)
                        self.validate_form()
                    return remove_selected

                def make_remove_all(lst, data):
                    def remove_all():
                        for _, encrypted_filename in data["files"]:
                            if encrypted_filename:
                                delete_encrypted_file(encrypted_filename)
                        data["files"] = []
                        update_file_list(lst, data)
                        self.validate_form()
                    return remove_all

                btn_layout = QHBoxLayout()
                add_btn = QPushButton("Aggiungi File")
                add_btn.clicked.connect(make_add_file(file_list, file_data))
                btn_layout.addWidget(add_btn)

                remove_btn = QPushButton("Rimuovi Selezionato")
                remove_btn.clicked.connect(make_remove_selected(file_list, file_data))
                btn_layout.addWidget(remove_btn)

                remove_all_btn = QPushButton("Rimuovi Tutti")
                remove_all_btn.clicked.connect(make_remove_all(file_list, file_data))
                btn_layout.addWidget(remove_all_btn)

                file_main_layout.addLayout(btn_layout)
                file_frame.setLayout(file_main_layout)
                form_layout.addWidget(file_frame)

                self.widgets[col_name] = {"type": "FILE", "data": file_data}
                
            elif spec_type == "RELATION":
                # Legacy RELATION support - treat as text field
                text_input = MultiLineTextEdit()
                if value is not None:
                    text_input.setPlainText(InputValidator.desanitize_text(str(value)))
                text_input.textChanged.connect(self.validate_form)
                form_layout.addWidget(text_input)
                self.widgets[col_name] = {"type": "TEXT", "widget": text_input}
                
            elif spec_type == "DATE":
                date_frame = QFrame()
                date_layout = QVBoxLayout()
                date_layout.setContentsMargins(0, 0, 0, 0)
                
                date_edit = QDateEdit()
                date_edit.setCalendarPopup(True)
                date_edit.setDate(QDate.fromString(str(value), "yyyy-MM-dd") if value else QDate.currentDate())
                date_edit.setDisplayFormat("yyyy-MM-dd")
                date_edit.dateChanged.connect(self.validate_form)
                date_layout.addWidget(date_edit)
                
                date_frame.setLayout(date_layout)
                form_layout.addWidget(date_frame)
                
                self.widgets[col_name] = {"type": "DATE", "widget": date_edit}
                
            else:
                col_type_from_pragma = col[2]
                
                if col_type_from_pragma == "REAL":
                    # For legacy REAL columns, use text edit (NUMERO type removed)
                    text_input = MultiLineTextEdit()
                    if value is not None:
                        text_input.setPlainText(InputValidator.desanitize_text(str(value)))
                    text_input.textChanged.connect(self.validate_form)
                    form_layout.addWidget(text_input)
                    self.widgets[col_name] = {"type": "TEXT", "widget": text_input}
                else:
                    # Use multiline text edit that allows any character
                    text_input = MultiLineTextEdit()
                    if value is not None:
                        text_input.setPlainText(InputValidator.desanitize_text(str(value)))
                    text_input.textChanged.connect(self.validate_form)
                    form_layout.addWidget(text_input)
                    self.widgets[col_name] = {"type": "TEXT", "widget": text_input}
        
        form_layout.addStretch()
        scroll_widget.setLayout(form_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        self.save_btn_ref = None
        
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.save_btn_ref = QPushButton("SALVA")
        self.save_btn_ref.clicked.connect(self.save_record)
        self.save_btn_ref.setEnabled(False)
        button_layout.addWidget(self.save_btn_ref)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.validate_form()
    
    def save_record(self):
        data = {}
        errors = []
        
        for col_name, widget_info in self.widgets.items():
            widget_type = widget_info["type"]
            
            if widget_type == "FILE":
                # Multi-file support: format list of files into DB string
                files_list = widget_info["data"].get("files", [])
                data[col_name] = format_multi_file_value(files_list) if files_list else None
            elif widget_type == "DATE":
                date_edit = widget_info["widget"]
                date_value = date_edit.date().toString("yyyy-MM-dd")
                is_valid, error_msg = InputValidator.validate_date(date_value)
                if not is_valid:
                    errors.append(f"{col_name}: {error_msg}")
                else:
                    data[col_name] = date_value
            elif isinstance(widget_info["widget"], QComboBox):
                value = widget_info["widget"].currentText()
                is_valid, error_msg = InputValidator.validate_text(value)
                if not is_valid:
                    errors.append(f"{col_name}: {error_msg}")
                else:
                    # Sanitize the combobox text input
                    data[col_name] = InputValidator.sanitize_text(value)
            else:
                # Handle both QLineEdit and QPlainTextEdit (MultiLineTextEdit)
                text_widget = widget_info["widget"]
                if hasattr(text_widget, 'toPlainText'):
                    value = text_widget.toPlainText()
                else:
                    value = text_widget.text()
                is_valid, error_msg = InputValidator.validate_text(value)
                if not is_valid:
                    errors.append(f"{col_name}: {error_msg}")
                else:
                    # Sanitize the text input to handle special characters
                    data[col_name] = InputValidator.sanitize_text(value)
        
        if errors:
            QMessageBox.warning(self, "Errore di Validazione", "\n".join(errors))
            return
        
        if self.record_id:
            # Before updating, handle file cleanup: if a FILE column had an old filename and
            # it's been replaced or removed, delete the old file copy from app/files
            try:
                old_record = self.db_manager.get_records(self.table_name, "id=?", (self.record_id,))
                if old_record:
                    cols = self.db_manager.get_columns(self.table_name)
                    # old_record[0] aligns with cols
                    for idx, col in enumerate(cols):
                        col_name = col[1]
                        spec = self.db_manager.get_special_type(self.table_name, col_name)
                        if spec and spec[0] == 'FILE':
                            old_val = old_record[0][idx]
                            new_val = data.get(col_name)
                            if old_val and (not new_val or new_val != old_val):
                                try:
                                    try:
                                        files_dir = get_files_dir()
                                        path_to_remove = os.path.join(files_dir, str(old_val))
                                    except Exception:
                                        files_dir = os.path.join(getattr(self.parent(), 'app_path', os.path.dirname(os.path.abspath(__file__))), 'files')
                                        path_to_remove = os.path.join(files_dir, str(old_val))
                                    if os.path.exists(path_to_remove):
                                        os.remove(path_to_remove)
                                except Exception:
                                    pass
            except Exception:
                pass

            if self.db_manager.update_record(self.table_name, self.record_id, data):
                QMessageBox.information(self, "Successo", "Record aggiornato!")
                self.accept()
            else:
                QMessageBox.warning(self, "Errore", "Errore nell'aggiornamento del record.")
        else:
            if self.db_manager.insert_record(self.table_name, data):
                QMessageBox.information(self, "Successo", "Record aggiunto!")
                self.accept()
            else:
                QMessageBox.warning(self, "Errore", "Errore nell'aggiunta del record.")
    
    def validate_form(self):
        errors = []
        
        for col_name, widget_info in self.widgets.items():
            widget_type = widget_info["type"]
            
            if widget_type == "FILE":
                # FILE columns are optional - no validation error if empty
                pass
            elif widget_type == "DATE":
                date_edit = widget_info["widget"]
                date_value = date_edit.date().toString("yyyy-MM-dd")
                is_valid, error_msg = InputValidator.validate_date(date_value)
                if not is_valid:
                    errors.append(f"{col_name}: {error_msg}")
            elif isinstance(widget_info["widget"], QComboBox):
                value = widget_info["widget"].currentText()
                if not value:
                    errors.append(f"{col_name}: Selezionare un valore")
            else:
                # Handle both QLineEdit and QPlainTextEdit (MultiLineTextEdit)
                text_widget = widget_info["widget"]
                if hasattr(text_widget, 'toPlainText'):
                    value = text_widget.toPlainText()
                else:
                    value = text_widget.text()
                is_valid, error_msg = InputValidator.validate_text(value)
                if not is_valid:
                    errors.append(f"{col_name}: {error_msg}")
        
        if errors:
            self.validation_label.setText("Attenzione: " + " | ".join(errors))
            if self.save_btn_ref:
                self.save_btn_ref.setEnabled(False)
        else:
            self.validation_label.setText("Tutti i campi sono validi")
            if self.save_btn_ref:
                self.save_btn_ref.setEnabled(True)
    
    def keyPressEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if self.save_btn_ref and self.save_btn_ref.isEnabled():
                self.save_record()
            else:
                event.ignore()
        else:
            super().keyPressEvent(event)


class AddColumnDialog(QDialog):
    def __init__(self, parent, db_manager: DatabaseManager, style_manager: StyleManager, table_name: str):
        super().__init__(parent)
        self.db_manager = db_manager
        self.style_manager = style_manager
        self.table_name = table_name
        
        self.setWindowTitle("Aggiungi Colonna")
        center_dialog(self, 0.35, 0.5)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("Aggiungi Nuova Colonna")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        layout.addWidget(QLabel("Nome Colonna:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome colonna...")
        layout.addWidget(self.name_input)
        
        layout.addWidget(QLabel("Tipo:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["TESTO", "DATA", "FILE"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        self.relation_frame = QFrame()
        relation_layout = QVBoxLayout()
        relation_layout.addWidget(QLabel("Tabella Correlata:"))
        self.relation_combo = QComboBox()
        relation_layout.addWidget(self.relation_combo)
        self.relation_frame.setLayout(relation_layout)
        self.relation_frame.hide()
        layout.addWidget(self.relation_frame)
        
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        add_btn = QPushButton("Aggiungi Colonna")
        add_btn.clicked.connect(self.add_column)
        button_layout.addWidget(add_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def on_type_changed(self):
        if self.type_combo.currentText() == "RELAZIONE":
            tables = [t for t in self.db_manager.get_tables() if t != self.table_name]
            self.relation_combo.clear()
            self.relation_combo.addItems(tables)
            self.relation_frame.show()
        else:
            self.relation_frame.hide()
    
    def add_column(self):
        col_name = self.name_input.text().strip()
        col_type = self.type_combo.currentText()
        
        if not col_name:
            QMessageBox.warning(self, "Errore", "Nome colonna necessario.")
            return
        
        # Controllo duplicati: verifica se esiste già una colonna con lo stesso nome
        existing_columns = self.db_manager.get_columns(self.table_name)
        existing_names = [col[1].lower() for col in existing_columns]
        if col_name.lower() in existing_names:
            QMessageBox.warning(self, "Errore", f"Esiste già una colonna con il nome '{col_name}'.")
            return
        
        sql_type = "TEXT"
        special_type = ""
        extra_info = ""
        
        if col_type == "FILE":
            sql_type = "TEXT"
            special_type = "FILE"
        elif col_type == "DATA":
            special_type = "DATE"
        
        if self.db_manager.add_column(self.table_name, col_name, sql_type, special_type, extra_info):
            QMessageBox.information(self, "Successo", f"Colonna '{col_name}' aggiunta!")
            self.accept()
        else:
            QMessageBox.warning(self, "Errore", "Errore nell'aggiunta della colonna.")
    
    def keyPressEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.add_column()
        else:
            super().keyPressEvent(event)



class PasswordDialog(QDialog):
    """Dialog shown at startup asking for the application password."""
    def __init__(self, parent, auth_path: str):
        super().__init__(parent)
        self.auth_path = auth_path
        self.setWindowTitle("Accesso")
        
        # Imposta icona se disponibile
        try:
            # Tenta di trovare il percorso dell'icona
            current_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(current_dir, "logo.png")
            if os.path.exists(logo_path):
                self.setWindowIcon(QIcon(logo_path))
        except Exception:
            pass
            
        # Dimensioni leggermente ridotte (30% larghezza, 18% altezza schermo)
        center_dialog(self, 0.30, 0.18)
        
        # Inizia trasparente per il fade-in
        self.setWindowOpacity(0.0)
        
        # Inizia trasparente per il fade-in
        self.setWindowOpacity(0.0)
        self.closing = False  # Flag per prevenire chiamate multiple a accept/reject
        
        self.init_ui()
        
        # Animazione fade-in
        QTimer.singleShot(0, self.start_fade_in)

    def start_fade_in(self):
        self.fade_in_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_anim.setDuration(400)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_in_anim.start()

    def accept(self):
        """Override accept to fade out first"""
        if self.closing:
            return
        self.closing = True
        print("[Auth] Accept called, starting fade-out")
        self.fade_out_and_close(lambda: self.done(1))  # 1 = Accepted
        
    def reject(self):
        """Override reject to fade out first"""
        if self.closing:
            return
        self.closing = True
        print("[Auth] Reject called, starting fade-out")
        self.fade_out_and_close(lambda: self.done(0))  # 0 = Rejected
        
    def fade_out_and_close(self, callback):
        self.fade_out_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(self.windowOpacity())
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_anim.finished.connect(callback)
        self.fade_out_anim.start()
        
        # Failsafe: se l'animazione si blocca, chiudi comunque dopo un timeout
        # Usiamo un timer non-singleShot che viene cancellato se finisce prima?
        # Semplice singleShot di sicurezza:
        QTimer.singleShot(500, callback) # 500ms > 300ms duration
        
        # Importante: se siamo in exec(), dobbiamo processare gli eventi
        # per permettere all'animazione di girare
        # Ma self.fade_out_anim.start() è asincrono? 
        # In exec() modale, l'event loop è gestito da Qt.
        # Dobbiamo solo assicurarci che non ritorni subito.
        # Sovrascrivendo accept/reject non chiamiamo super() subito, 
        # quindi la finestra rimane aperta mentre l'animazione gira.
        # Quando 'finished' chiama callback (super().accept), allora si chiude.

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Inserisci la password per accedere:"))

        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.returnPressed.connect(self.try_accept)
        # Give focus to the password field so the user can type immediately
        self.pwd_input.setFocus()
        self.pwd_input.setFocus()
        layout.addWidget(self.pwd_input)
        
        # Etichetta per errori inline (inizialmente nascosta/vuota)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff5555; font-size: 11px; font-weight: bold;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Accedi")
        ok_btn.clicked.connect(self.try_accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        
        # Make Accedi default and prevent cancel on Enter
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        cancel_btn.setAutoDefault(False)

    def keyPressEvent(self, event):
        # Impedisci che Esc chiuda la finestra
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def try_accept(self):
        import auth as auth_mod
        pwd = self.pwd_input.text().strip()
        
        # Reset errore
        self.error_label.setText("")
        
        try:
            ok = auth_mod.verify_password(self.auth_path, pwd)
        except Exception:
            ok = False

        if ok:
            # Chiama self.accept() che ora include il fade-out
            self.accept()
            return

        # Mostra errore inline invece di popup
        # Questo evita che l'utente chiuda per sbaglio il dialog premendo Esc/Enter sul popup
        self.error_label.setText("Password errata")
        
        # Pulisce il campo password
        self.pwd_input.clear()
        self.pwd_input.setFocus()
        
        # Non chiamare self.reject() o self.close() qui!
        # La finestra deve rimanere aperta per il retry.


class ChangePasswordDialog(QDialog):
    """Dialog to allow the user to change the application password."""
    def __init__(self, parent, auth_path: str):
        super().__init__(parent)
        self.auth_path = auth_path
        self.setWindowTitle("Cambia Password")
        center_dialog(self, 0.4, 0.35)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Password attuale:"))
        self.current_input = QLineEdit()
        self.current_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.current_input)

        layout.addWidget(QLabel("Nuova password (solo lettere e numeri):"))
        self.new_input = QLineEdit()
        self.new_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.new_input)

        layout.addWidget(QLabel("Conferma nuova password:"))
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_input)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Aggiorna")
        ok_btn.clicked.connect(self.try_change)
        # Make the OK button the default so Enter triggers it when the dialog is focused
        try:
            ok_btn.setDefault(True)
            ok_btn.setAutoDefault(True)
        except Exception:
            pass

        # Connect Enter key on inputs to trigger password change
        try:
            self.current_input.returnPressed.connect(self.try_change)
            self.new_input.returnPressed.connect(self.try_change)
            self.confirm_input.returnPressed.connect(self.try_change)
        except Exception:
            pass

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def try_change(self):
        import re
        import auth as auth_mod
        from PyQt6.QtWidgets import QMessageBox

        current = self.current_input.text().strip()
        new = self.new_input.text().strip()
        confirm = self.confirm_input.text().strip()

        # Verify current password
        try:
            current_ok = auth_mod.verify_password(self.auth_path, current)
        except Exception:
            current_ok = False

        if not current_ok:
            QMessageBox.warning(self, "Errore", "Password attuale errata")
            try:
                print(f"[auth-change] current verification failed for path={self.auth_path}")
            except Exception:
                pass
            return

        if new != confirm:
            QMessageBox.warning(self, "Errore", "Le password non coincidono")
            return

        # Validate allowed characters: only letters (upper/lower) and digits
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]+$', new):
            QMessageBox.warning(self, "Errore", "La nuova password deve contenere solo lettere e numeri, almeno una lettera e un numero")
            return

        if len(new) < 4:
            QMessageBox.warning(self, "Errore", "La password deve essere lunga almeno 4 caratteri")
            return

        # Try to write the new password
        try:
            written = auth_mod.set_password(self.auth_path, new)
        except Exception:
            written = False

        # Post-write verification
        try:
            verify_after = auth_mod.verify_password(self.auth_path, new)
        except Exception:
            verify_after = False

        try:
            print(f"[auth-change] path={self.auth_path} written={written} verify_after={verify_after}")
        except Exception:
            pass

        if written and verify_after:
            QMessageBox.information(self, "Successo", "Password aggiornata")
            self.accept()
        else:
            # Provide a more detailed failure reason in the UI
            if not written:
                detail = "Errore nella scrittura del file di autenticazione. Controlla permessi e spazio su disco."
            elif not verify_after:
                detail = "La password è stata scritta ma non è possibile verificarla immediatamente (file corrotto o permessi)."
            else:
                detail = "Errore sconosciuto durante l'aggiornamento della password."

            try:
                print(f"[auth-change] failure detail: written={written} verify_after={verify_after} path={self.auth_path}")
            except Exception:
                pass

            QMessageBox.warning(self, "Errore", f"Impossibile aggiornare la password: {detail}")
