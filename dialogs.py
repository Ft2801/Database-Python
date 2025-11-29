from typing import Tuple
import os
from file_utils import get_files_dir, encrypt_file, parse_file_value, format_file_value, delete_encrypted_file
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QListWidget, QFrame, QScrollArea, QWidget, QMessageBox,
    QFileDialog, QDateEdit, QDoubleSpinBox, QApplication
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QFont, QPixmap

from validators import InputValidator
from config import StyleManager
from database import DatabaseManager


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
                    "• Premi Invio per salvare le modifiche",
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
                    "• Tipi disponibili: TESTO, NUMERO, DATA, FILE, RELAZIONE",
                    "• Le colonne RELAZIONE collegano i dati tra tabelle diverse"
                ]
            },
            {
                "title": "Scorciatoie da Tastiera",
                "content": [
                    "• Ctrl+Z: Annulla l'ultima operazione (max 3)",
                    "• Ctrl+Shift+Z: Ripristina l'operazione annullata",
                    "• Invio: Salva la modifica nella cella o nel campo data",
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
                    "• Il feedback appare nella barra di stato (undo/redo)"
                ]
            },
            {
                "title": "Backup e Importazione",
                "content": [
                    "• Backup: Crea una copia di sicurezza del database",
                    "• Esporta: Esporta una tabella in formato CSV",
                    "• Importa: Importa dati da un file CSV"
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
        InputValidator.restrict_input(self.name_input, r'^[a-zA-Z0-9_]*$')
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
        InputValidator.restrict_input(self.col_name_input, r'^[a-zA-Z0-9_]*$')
        input_layout.addWidget(col_name_label)
        input_layout.addWidget(self.col_name_input)
        
        type_label = QLabel("Tipo:")
        self.col_type_combo = QComboBox()
        self.col_type_combo.addItems(["TESTO", "NUMERO", "DATA", "FILE", "RELAZIONE"])
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
        col_name = self.col_name_input.text().strip().replace(" ", "_")
        col_type = self.col_type_combo.currentText()
        
        if not col_name:
            return
        
        # Controllo duplicati: verifica se esiste già una colonna con lo stesso nome
        existing_names = [col['name'].lower() for col in self.columns]
        if col_name.lower() in existing_names:
            QMessageBox.warning(self, "Errore", f"Esiste già una colonna con il nome '{col_name}'.")
            return
        
        if col_type == "RELAZIONE":
            tables = self.db_manager.get_tables()
            if not tables:
                QMessageBox.warning(self, "Errore", "Nessuna tabella disponibile per il collegamento.")
                return
            
            relation_dialog = QDialog(self)
            relation_dialog.setWindowTitle("Collegamento a tabella")
            
            rel_layout = QVBoxLayout()
            rel_layout.addWidget(QLabel("Seleziona tabella di destinazione:"))
            
            table_combo = QComboBox()
            table_combo.addItems(tables)
            rel_layout.addWidget(table_combo)
            
            def confirm_relation():
                target = table_combo.currentText()
                self.columns.append({
                    'name': col_name,
                    'sql_type': 'TEXT',
                    'special': 'RELATION',
                    'extra': target
                })
                self.update_columns_list()
                self.col_name_input.clear()
                relation_dialog.accept()
            
            ok_btn = QPushButton("OK")
            ok_btn.clicked.connect(confirm_relation)
            rel_layout.addWidget(ok_btn)
            
            relation_dialog.setLayout(rel_layout)
            relation_dialog.exec()
            return
        
        sql_type = "TEXT"
        special = ""
        
        if col_type == "NUMERO":
            sql_type = "REAL"
        elif col_type == "FILE":
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
        table_name = self.name_input.text().strip().replace(" ", "_")
        
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
                # File picker: encrypt and copy selected file into app's files/ folder
                import uuid
                file_frame = QFrame()
                file_layout = QHBoxLayout()

                file_label = QLabel("Nessun file selezionato")
                file_label.setMinimumHeight(24)
                file_layout.addWidget(file_label)

                # widget data keeps the DB value (original_name|encrypted_filename) and a flag
                file_data = {"filename": value, "remove_old": False}

                # If an existing file value is present, show only the original name
                if value:
                    original_name, _ = parse_file_value(str(value))
                    file_label.setText(original_name if original_name else str(value))

                def make_choose_file(lbl, data):
                    def choose_file():
                        src_path, _ = QFileDialog.getOpenFileName(self, "Seleziona File", "", "Tutti i file (*.*)")
                        if src_path:
                            try:
                                # Delete old file if replacing
                                old_value = data.get('filename')
                                if old_value:
                                    _, old_encrypted = parse_file_value(str(old_value))
                                    if old_encrypted:
                                        delete_encrypted_file(old_encrypted)
                                
                                files_dir = get_files_dir()
                                original_name = os.path.basename(src_path)
                                # Create encrypted filename with .enc extension
                                encrypted_name = f"{uuid.uuid4().hex}.enc"
                                dest_path = os.path.join(files_dir, encrypted_name)
                                # Encrypt and save the file
                                if encrypt_file(src_path, dest_path):
                                    # Store as "original_name|encrypted_filename"
                                    db_value = format_file_value(original_name, encrypted_name)
                                    data['filename'] = db_value
                                    data['remove_old'] = True
                                    # Show only original name in UI
                                    lbl.setText(original_name)
                            except Exception:
                                pass
                        self.validate_form()
                    return choose_file

                def make_remove_file(lbl, data):
                    def remove_file():
                        if data.get('filename'):
                            # Delete the physical file
                            _, encrypted_filename = parse_file_value(str(data['filename']))
                            if encrypted_filename:
                                delete_encrypted_file(encrypted_filename)
                            data['filename'] = None
                            data['remove_old'] = True
                        lbl.setText("Nessun file selezionato")
                        self.validate_form()
                    return remove_file

                choose_btn = QPushButton("Scegli File")
                choose_btn.setMaximumWidth(120)
                choose_btn.clicked.connect(make_choose_file(file_label, file_data))
                file_layout.addWidget(choose_btn)

                remove_btn = QPushButton("Rimuovi File")
                remove_btn.setMaximumWidth(120)
                remove_btn.clicked.connect(make_remove_file(file_label, file_data))
                file_layout.addWidget(remove_btn)

                file_frame.setLayout(file_layout)
                form_layout.addWidget(file_frame)

                self.widgets[col_name] = {"type": "FILE", "data": file_data}
                
            elif spec_type == "RELATION":
                target_table = spec_info[1]
                target_cols = self.db_manager.get_columns(target_table)
                disp_col_idx = 1 if len(target_cols) > 1 else 0
                
                target_records = self.db_manager.get_records(target_table)
                options = [str(rec[disp_col_idx]) for rec in target_records]
                
                combo = QComboBox()
                combo.addItems(options)
                if value:
                    combo.setCurrentText(str(value))
                combo.currentTextChanged.connect(self.validate_form)
                form_layout.addWidget(combo)
                
                self.widgets[col_name] = {"type": "TEXT", "widget": combo}
                
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
                    number_input = QDoubleSpinBox()
                    number_input.setMinimum(-999999999.99)
                    number_input.setMaximum(999999999.99)
                    number_input.setDecimals(2)
                    if value is not None:
                        number_input.setValue(float(value) if value else 0.0)
                    number_input.valueChanged.connect(self.validate_form)
                    form_layout.addWidget(number_input)
                    self.widgets[col_name] = {"type": "NUMBER", "widget": number_input}
                else:
                    text_input = QLineEdit()
                    if value is not None:
                        text_input.setText(str(value))
                    InputValidator.restrict_input(text_input, r'^[a-zA-Z0-9\s\-._@]*$')
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
                data[col_name] = widget_info["data"].get("filename")
            elif widget_type == "DATE":
                date_edit = widget_info["widget"]
                date_value = date_edit.date().toString("yyyy-MM-dd")
                is_valid, error_msg = InputValidator.validate_date(date_value)
                if not is_valid:
                    errors.append(f"{col_name}: {error_msg}")
                else:
                    data[col_name] = date_value
            elif widget_type == "NUMBER":
                number_widget = widget_info["widget"]
                value = number_widget.value()
                data[col_name] = value
            elif isinstance(widget_info["widget"], QComboBox):
                value = widget_info["widget"].currentText()
                is_valid, error_msg = InputValidator.validate_text(value)
                if not is_valid:
                    errors.append(f"{col_name}: {error_msg}")
                else:
                    data[col_name] = value
            else:
                text_widget = widget_info["widget"]
                value = text_widget.text()
                is_valid, error_msg = InputValidator.validate_text(value)
                if not is_valid:
                    errors.append(f"{col_name}: {error_msg}")
                else:
                    data[col_name] = value
        
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
            elif widget_type == "NUMBER":
                number_widget = widget_info["widget"]
                value = number_widget.value()
                if value == 0.0 and str(number_widget.value()) not in ["0.0", "0"]:
                    errors.append(f"{col_name}: Numero non valido")
            elif isinstance(widget_info["widget"], QComboBox):
                value = widget_info["widget"].currentText()
                if not value:
                    errors.append(f"{col_name}: Selezionare un valore")
            else:
                text_widget = widget_info["widget"]
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
        InputValidator.restrict_input(self.name_input, r'^[a-zA-Z0-9_]*$')
        layout.addWidget(self.name_input)
        
        layout.addWidget(QLabel("Tipo:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["TESTO", "NUMERO", "DATA", "FILE", "RELAZIONE"])
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
        col_name = self.name_input.text().strip().replace(" ", "_")
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
        
        if col_type == "NUMERO":
            sql_type = "REAL"
        elif col_type == "FILE":
            sql_type = "TEXT"
            special_type = "FILE"
        elif col_type == "DATA":
            special_type = "DATE"
        elif col_type == "RELAZIONE":
            special_type = "RELATION"
            extra_info = self.relation_combo.currentText()
        
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
        center_dialog(self, 0.35, 0.25)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Inserisci la password per accedere:"))

        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.returnPressed.connect(self.try_accept)
        # Give focus to the password field so the user can type immediately
        self.pwd_input.setFocus()
        layout.addWidget(self.pwd_input)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Accedi")
        ok_btn.clicked.connect(self.try_accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def try_accept(self):
        import auth as auth_mod
        pwd = self.pwd_input.text().strip()
        try:
            ok = auth_mod.verify_password(self.auth_path, pwd)
        except Exception:
            ok = False

        if ok:
            self.accept()
            return

        # Debug hint (printed to console) for diagnosis; kept minimal
        try:
            print(f"[auth] verify failed for input (len={len(pwd)}) against {self.auth_path}")
        except Exception:
            pass

        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Accesso negato", "Password errata")


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
