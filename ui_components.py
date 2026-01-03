from typing import Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QComboBox, QHeaderView, QMessageBox, QMenu, QPlainTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QAction

from ui_delegates import EditableTableDelegate
from validators import InputValidator
from config import THEMES, StyleManager
from database import DatabaseManager

import os
import subprocess
import sys
from file_utils import get_files_dir, parse_file_value, decrypt_file_to_temp, parse_multi_file_value, get_display_names_from_multi_file


class CellTextEdit(QPlainTextEdit):
    """Custom text edit for table cell editing. Enter saves, Shift+Enter adds newline."""
    save_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setMaximumHeight(150)
    
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter inserts newline
                super().keyPressEvent(event)
            else:
                # Enter saves
                self.save_requested.emit()
        else:
            super().keyPressEvent(event)


class NavBar(QFrame):
    backup_requested = pyqtSignal()
    tutorial_requested = pyqtSignal()
    password_change_requested = pyqtSignal()
    
    def __init__(self, style_manager: StyleManager):
        super().__init__()
        self.style_manager = style_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(20)
        
        title = QLabel("Gestione Database")
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        title.setFont(title_font)
        # default label color
        
        layout.addWidget(title)
        layout.addStretch()
        
        backup_btn = QPushButton("Backup")
        # use default button styling
        backup_btn.clicked.connect(self.backup_requested.emit)
        layout.addWidget(backup_btn)
        
        tutorial_btn = QPushButton("Tutorial")
        # use default button styling
        tutorial_btn.clicked.connect(self.tutorial_requested.emit)
        layout.addWidget(tutorial_btn)
        change_pwd_btn = QPushButton("Cambia Password")
        change_pwd_btn.clicked.connect(self.password_change_requested.emit)
        layout.addWidget(change_pwd_btn)
        
        self.setLayout(layout)
        # keep NavBar default frame styling


class SideBar(QFrame):
    table_selected = pyqtSignal(str)
    new_table = pyqtSignal()
    delete_table = pyqtSignal()
    
    def __init__(self, style_manager: StyleManager, db_manager: DatabaseManager):
        super().__init__()
        self.setObjectName("sidebarFrame")
        self.style_manager = style_manager
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        title = QLabel("Tabelle")
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        title.setFont(title_font)
        # default label color
        layout.addWidget(title)
        
        self.table_list = QListWidget()
        self.table_list.itemSelectionChanged.connect(self.on_table_selected)
        layout.addWidget(self.table_list)
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)
        
        new_btn = QPushButton("Nuova Tabella")
        # default button style
        new_btn.clicked.connect(self.new_table.emit)
        btn_layout.addWidget(new_btn)
        
        del_btn = QPushButton("Elimina Tabella")
        # default button style
        del_btn.clicked.connect(self.delete_table.emit)
        btn_layout.addWidget(del_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setMaximumWidth(280)
        # keep SideBar default frame styling
    
    def load_tables(self):
        self.table_list.blockSignals(True)
        self.table_list.clear()
        for table in self.db_manager.get_tables():
            self.table_list.addItem(table)
        self.table_list.blockSignals(False)
    
    def on_table_selected(self):
        if self.table_list.currentItem():
            self.table_selected.emit(self.table_list.currentItem().text())
    
    def get_selected_table(self) -> Optional[str]:
        if self.table_list.currentItem():
            return self.table_list.currentItem().text()
        return None


class MainArea(QFrame):
    def __init__(self, style_manager: StyleManager, db_manager: DatabaseManager):
        super().__init__()
        self.style_manager = style_manager
        self.db_manager = db_manager
        self.current_table = None
        self.setObjectName("mainAreaFrame")
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Seleziona una tabella per visualizzare i dati")
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        # default label color
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        search_label = QLabel("Cerca:")
        self.search_input = QLineEdit()
        self.search_input.setMaximumWidth(200)
        self.search_input.setPlaceholderText("Cerca...")
        # No restriction on search input - allow any characters
        
        header_layout.addWidget(search_label)
        header_layout.addWidget(self.search_input)
        
        layout.addLayout(header_layout)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.new_btn = self.create_button("Nuovo Record", self.style_manager.colors['success'])
        self.edit_btn = self.create_button("Modifica", self.style_manager.colors['primary'])
        self.del_btn = self.create_button("Elimina", self.style_manager.colors['danger'])
        self.col_btn = self.create_button("Aggiungi Colonna", self.style_manager.colors['warning'])
        
        for btn in [self.new_btn, self.edit_btn, self.del_btn, self.col_btn]:
            buttons_layout.addWidget(btn)
            btn.setEnabled(False)
        
        layout.addLayout(buttons_layout)
        
        self.table_widget = QTableWidget()
        # enable custom context menu for file actions
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.on_table_context_menu)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        # Disable alternating row colors so we can apply a uniform row color per theme
        self.table_widget.setAlternatingRowColors(False)
        self.table_widget.setShowGrid(True)
        self.table_widget.setGridStyle(Qt.PenStyle.SolidLine)
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.table_widget.keyPressEvent = self.table_key_press_event
        self.table_widget.verticalHeader().setStretchLastSection(False)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Enable word wrap for multiline text display in cells
        self.table_widget.setWordWrap(True)
        
        # Abilita il doppio click sugli header per rinominare le colonne
        self.table_widget.horizontalHeader().sectionDoubleClicked.connect(self.rename_column)
        
        # Abilita lo spostamento visuale delle colonne
        self.table_widget.horizontalHeader().setSectionsMovable(True)
        self.table_widget.horizontalHeader().setDragEnabled(True)
        
        layout.addWidget(self.table_widget)
        
        self.setLayout(layout)
        # keep MainArea default frame styling
        # Apply theme-specific styles for the table (uniform row colors)
        try:
            self.apply_theme_styles()
        except Exception:
            pass

    def get_column_state(self):
        """Restituisce lo stato visivo delle colonne come stringa base64"""
        if not self.current_table:
            return None
        return self.table_widget.horizontalHeader().saveState().toBase64().data().decode('utf-8')

    def set_column_state(self, state_b64):
        """Ripristina lo stato visivo delle colonne"""
        if not state_b64 or not self.current_table:
            return
        try:
            from PyQt6.QtCore import QByteArray
            import base64
            # Convert string back to bytes
            data = QByteArray(base64.b64decode(state_b64))
            self.table_widget.horizontalHeader().restoreState(data)
        except Exception as e:
            print(f"Error restoring column state: {e}")
    
    def create_button(self, text: str, color: str) -> QPushButton:
        btn = QPushButton(text)
        # default button appearance
        return btn

    def apply_theme_styles(self):
        """Ensure alternating rows are disabled for uniform appearance."""
        self.table_widget.setAlternatingRowColors(False)
    
    def load_table(self, table_name: str):
        self.current_table = table_name
        self.title_label.setText(f"Tabella: {table_name}")
        self.refresh_table_data()
        
        for btn in [self.new_btn, self.edit_btn, self.del_btn, self.col_btn]:
            btn.setEnabled(True)
    
    def refresh_table_data(self):
        if not self.current_table:
            return

        try:
            columns = self.db_manager.get_columns(self.current_table)
        except Exception:
            QMessageBox.warning(self, "Errore", f"La tabella '{self.current_table}' non esiste.")
            self.current_table = None
            self.title_label.setText("Seleziona una tabella")
            return

        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)
        # Salto la prima colonna (ID) dalla visualizzazione
        col_names = [col[1] for col in columns[1:]]
        
        self.table_widget.setColumnCount(len(col_names))
        self.table_widget.setHorizontalHeaderLabels(col_names)
        
        records = self.db_manager.get_records(self.current_table)
        
        self.table_widget.setRowCount(len(records))
        
        for row_idx, record in enumerate(records):
            record_id = record[0]
            # Salto il primo valore (ID) dalla visualizzazione
            for col_idx, value in enumerate(record[1:]):
                col_name = col_names[col_idx]
                spec_type = self.db_manager.get_special_type(self.current_table, col_name)
                
                if spec_type and spec_type[0] == "FILE" and value is not None:
                    # Display multi-file names (comma-separated)
                    display_names = get_display_names_from_multi_file(str(value))
                    item = QTableWidgetItem(display_names if display_names else "[Nessun file]")
                    # Store full DB value for file operations
                    item.setData(Qt.ItemDataRole.UserRole + 1, str(value))
                else:
                    # Decode sanitized text for display
                    from validators import InputValidator
                    display_value = InputValidator.desanitize_text(str(value)) if value is not None else ""
                    item = QTableWidgetItem(display_value)
                
                item.setData(Qt.ItemDataRole.UserRole, record_id)
                self.table_widget.setItem(row_idx, col_idx, item)
                self.adjust_row_height(row_idx)
        
        for col_idx in range(len(col_names)):
            self.table_widget.setColumnWidth(col_idx, 150)
        
        self.table_widget.setItemDelegate(EditableTableDelegate())
        self.table_widget.resizeRowsToContents()
    
    def adjust_row_height(self, row_idx: int):
        self.table_widget.resizeRowToContents(row_idx)
        current_height = self.table_widget.rowHeight(row_idx)
        if current_height < 30:
            self.table_widget.setRowHeight(row_idx, 30)
        elif current_height > 300:
            self.table_widget.setRowHeight(row_idx, 300)
    
    def table_key_press_event(self, event):
        from PyQt6.QtGui import QKeySequence
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            selected_indexes = self.table_widget.selectedIndexes()
            if selected_indexes:
                item = self.table_widget.itemFromIndex(selected_indexes[0])
                if item:
                    self.edit_cell(item)
                    return
        # Chiama il metodo originale della classe base
        QTableWidget.keyPressEvent(self.table_widget, event)
    
    def edit_cell(self, item):
        row = item.row()
        col = item.column()
        columns = self.db_manager.get_columns(self.current_table)
        # Salto la prima colonna (ID)
        col_name = columns[col + 1][1]
        
        spec_type = self.db_manager.get_special_type(self.current_table, col_name)
        spec_type_name = spec_type[0] if spec_type else None
        
        if spec_type_name == "DATE":
            self.edit_date_cell(item)
        elif spec_type_name == "FILE":
            # Open encrypted file on double-click
            # Get full DB value from item data
            db_value = item.data(Qt.ItemDataRole.UserRole + 1)
            if db_value:
                self.show_file_selection_dialog(db_value)
            else:
                QMessageBox.information(self, "Info", "Nessun file associato a questa cella")
        else:
            # All other column types use text editing (including legacy REAL columns)
            self.edit_text_cell(item)
    
    def edit_text_cell(self, item):
        from PyQt6.QtWidgets import QDialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifica Cella")
        dialog.setGeometry(300, 300, 450, 250)
        # use default dialog styling
        
        layout = QVBoxLayout()
        hint_label = QLabel("Valore (Shift+Invio per nuova riga, Invio per salvare):")
        layout.addWidget(hint_label)
        
        editor = CellTextEdit()
        editor.setPlainText(item.text())
        layout.addWidget(editor)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        editor.save_requested.connect(dialog.accept)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row = item.row()
            col = item.column()
            new_text = editor.toPlainText()
            # Sanitize the text before saving
            sanitized_text = InputValidator.sanitize_text(new_text)
            # Store the sanitized text in the model so it stays consistent with the database
            item.setText(sanitized_text)
            self.adjust_row_height(row)
            self.table_widget.resizeRowsToContents()
            
            record_id = item.data(Qt.ItemDataRole.UserRole)
            if record_id is not None:
                columns = self.db_manager.get_columns(self.current_table)
                col_name = columns[col + 1][1]
                self.db_manager.update_record(self.current_table, record_id, {col_name: sanitized_text})
            
            self.table_widget.clearSelection()
    
    def edit_date_cell(self, item):
        from PyQt6.QtWidgets import QDialog, QDateEdit
        from PyQt6.QtCore import QDate
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifica Data")
        dialog.setGeometry(300, 300, 400, 180)
        # use default dialog styling
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Seleziona Data (aaaa-MM-gg):"))
        
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("yyyy-MM-dd")
        
        current_text = item.text()
        try:
            current_date = QDate.fromString(current_text, "yyyy-MM-dd")
            if current_date.isValid():
                date_edit.setDate(current_date)
            else:
                date_edit.setDate(QDate.currentDate())
        except:
            date_edit.setDate(QDate.currentDate())
        
        layout.addWidget(date_edit)
        
        error_label = QLabel("")
        layout.addWidget(error_label)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn = QPushButton("OK")
        
        def on_ok_clicked():
            selected_date = date_edit.date()
            if not selected_date.isValid():
                error_label.setText("Data non valida")
                return
            date_str = selected_date.toString("yyyy-MM-dd")
            row = item.row()
            col = item.column()
            item.setText(date_str)
            self.adjust_row_height(row)
            self.table_widget.resizeRowsToContents()
            
            record_id = item.data(Qt.ItemDataRole.UserRole)
            if record_id is not None:
                columns = self.db_manager.get_columns(self.current_table)
                col_name = columns[col + 1][1]
                self.db_manager.update_record(self.current_table, record_id, {col_name: date_str})
            
            self.table_widget.clearSelection()
            dialog.accept()
        
        ok_btn.clicked.connect(on_ok_clicked)
        
        # Gestisco il tasto Invio tramite eventFilter
        def date_key_filter(watched, event):
            from PyQt6.QtCore import QEvent
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    on_ok_clicked()
                    return True
            return False
        
        date_edit.keyPressEvent = lambda event: (
            on_ok_clicked() if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) 
            else QDateEdit.keyPressEvent(date_edit, event)
        )
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec()

    def on_item_double_clicked(self, item):
        """Handle double click on table items. For FILE columns open in explorer, otherwise delegate to edit_cell."""
        row = item.row()
        col = item.column()
        columns = self.db_manager.get_columns(self.current_table)
        col_name = columns[col + 1][1]
        spec_type = self.db_manager.get_special_type(self.current_table, col_name)
        spec_type_name = spec_type[0] if spec_type else None

        if spec_type_name == 'FILE':
            # Get full DB value from item data
            db_value = item.data(Qt.ItemDataRole.UserRole + 1)
            if db_value:
                self.show_file_selection_dialog(db_value)
            else:
                QMessageBox.information(self, "Info", "Nessun file associato a questa cella")
            return

        # fallback to existing behavior
        self.edit_cell(item)

    def on_table_context_menu(self, pos):
        """Show context menu for file actions when right-clicking table rows."""
        index = self.table_widget.indexAt(pos)
        if not index.isValid():
            return

        item = self.table_widget.itemFromIndex(index)
        if not item:
            return

        row = index.row()
        col = index.column()
        columns = self.db_manager.get_columns(self.current_table)
        col_name = columns[col + 1][1]
        spec = self.db_manager.get_special_type(self.current_table, col_name)
        spec_name = spec[0] if spec else None

        menu = QMenu(self)
        if spec_name == 'FILE':
            # Get full DB value from item data
            db_value = item.data(Qt.ItemDataRole.UserRole + 1)
            if db_value:
                open_action = QAction("Apri File", self)
                open_action.triggered.connect(lambda: self.show_file_selection_dialog(db_value))
                menu.addAction(open_action)
            else:
                info_action = QAction("Nessun file", self)
                info_action.setEnabled(False)
                menu.addAction(info_action)

        # Always add a generic Edit action
        edit_action = QAction("Modifica", self)
        edit_action.triggered.connect(lambda: self.edit_cell(item))
        menu.addAction(edit_action)

        menu.exec(self.table_widget.viewport().mapToGlobal(pos))

    def show_file_selection_dialog(self, db_value: str):
        """Show a dialog to select which file to open when multiple files exist."""
        from PyQt6.QtWidgets import QDialog, QListWidget
        
        files = parse_multi_file_value(db_value)
        
        if not files:
            QMessageBox.information(self, "Info", "Nessun file associato")
            return
        
        if len(files) == 1:
            # Only one file, open it directly
            self.open_single_file(files[0][0], files[0][1])
            return
        
        # Multiple files - show selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleziona File da Aprire")
        dialog.setGeometry(300, 300, 400, 300)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Seleziona il file da aprire:"))
        
        file_list = QListWidget()
        for orig, _ in files:
            file_list.addItem(orig)
        layout.addWidget(file_list)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(dialog.reject)
        open_btn = QPushButton("Apri")
        
        def open_selected():
            current_row = file_list.currentRow()
            if current_row >= 0:
                orig, enc = files[current_row]
                dialog.accept()
                self.open_single_file(orig, enc)
        
        open_btn.clicked.connect(open_selected)
        file_list.itemDoubleClicked.connect(open_selected)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(open_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec()

    def open_single_file(self, original_name: str, encrypted_filename: str):
        """Open a single encrypted file."""
        try:
            # Decrypt file to temp location
            temp_path = decrypt_file_to_temp(encrypted_filename, original_name or encrypted_filename)
            
            if not temp_path or not os.path.exists(temp_path):
                QMessageBox.warning(self, "Errore", "Impossibile decriptare il file")
                return
            
            # Open with default application
            try:
                if sys.platform.startswith('win'):
                    os.startfile(temp_path)
                elif sys.platform.startswith('darwin'):
                    subprocess.run(['open', temp_path], check=False)
                else:
                    subprocess.run(['xdg-open', temp_path], check=False)
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Impossibile aprire il file: {e}")
                
            # Note: temp file will remain until system cleans it up
            # This is intentional so the app can finish opening before deletion
            
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore nell'apertura del file: {e}")

    def open_file_in_explorer(self, filename: str):
        try:
            files_dir = get_files_dir()
            full_path = os.path.join(files_dir, filename)
        except Exception:
            # fallback to app dir
            try:
                app_dir = os.path.dirname(os.path.abspath(__file__))
                full_path = os.path.join(app_dir, 'files', filename)
            except Exception:
                QMessageBox.warning(self, "Errore", "Impossibile determinare il percorso del file")
                return

        full_path = os.path.abspath(full_path)

        if not os.path.exists(full_path):
            QMessageBox.warning(self, "File mancante", f"Il file non è stato trovato: {full_path}")
            print(f"[open_file_in_explorer] missing: {full_path}")
            return

        try:
            if sys.platform.startswith('win'):
                # explorer with select. Use a single argument '/select,<path>' which is accepted by explorer
                cmd = ['explorer', f'/select,{full_path}']
                print(f"[open_file_in_explorer] running: {cmd}")
                subprocess.run(cmd, check=False)
            else:
                # Try to open the folder containing the file
                folder = os.path.dirname(full_path)
                if sys.platform.startswith('darwin'):
                    cmd = ['open', folder]
                else:
                    cmd = ['xdg-open', folder]
                print(f"[open_file_in_explorer] running: {cmd}")
                subprocess.run(cmd, check=False)
        except Exception as e:
            print(f"[open_file_in_explorer] primary open failed: {e}")
            try:
                # fallback: open the file with default app
                if sys.platform.startswith('win'):
                    print(f"[open_file_in_explorer] fallback os.startfile: {full_path}")
                    os.startfile(full_path)
                else:
                    subprocess.run(['xdg-open', full_path], check=False)
            except Exception as e2:
                print(f"[open_file_in_explorer] fallback open failed: {e2}")
                QMessageBox.warning(self, "Errore", "Impossibile aprire il file o la cartella")
    
    def edit_number_cell(self, item):
        from PyQt6.QtWidgets import QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifica Numero")
        dialog.setGeometry(300, 300, 400, 150)
        # use default dialog styling
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Valore (usa . per i decimali):"))
        
        editor = QLineEdit()
        editor.setText(item.text() if item.text() else "0.0")
        InputValidator.restrict_number_input(editor)
        layout.addWidget(editor)
        
        error_label = QLabel("")
        layout.addWidget(error_label)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn = QPushButton("OK")
        
        def on_ok_clicked():
            try:
                value = float(editor.text()) if editor.text() else 0.0
                row = item.row()
                col = item.column()
                item.setText(str(value))
                self.adjust_row_height(row)
                self.table_widget.resizeRowsToContents()
                
                record_id = item.data(Qt.ItemDataRole.UserRole)
                if record_id is not None:
                    columns = self.db_manager.get_columns(self.current_table)
                    # +1 perché saltiamo la colonna ID
                    col_name = columns[col + 1][1]
                    self.db_manager.update_record(self.current_table, record_id, {col_name: str(value)})
                
                self.table_widget.clearSelection()
                dialog.accept()
            except ValueError:
                error_label.setText("Numero non valido")
        
        ok_btn.clicked.connect(on_ok_clicked)
        editor.returnPressed.connect(on_ok_clicked)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def rename_column(self, column_index: int):
        """Rinomina una colonna con doppio click sull'header"""
        if not self.current_table:
            return
        
        columns = self.db_manager.get_columns(self.current_table)
        # +1 perché saltiamo la colonna ID
        old_name = columns[column_index + 1][1]
        
        from PyQt6.QtWidgets import QDialog
        
        # Crea dialog personalizzata con stile
        dialog = QDialog(self)
        dialog.setWindowTitle("Rinomina Colonna")
        dialog.setGeometry(300, 300, 400, 180)
        # default dialog styling
        
        layout = QVBoxLayout()
        
        title = QLabel(f"Rinomina Colonna '{old_name}'")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(title)
        
        layout.addWidget(QLabel("Nuovo nome:"))
        
        name_input = QLineEdit()
        name_input.setText(old_name)
        name_input.selectAll()
        layout.addWidget(name_input)
        
        error_label = QLabel("")
        layout.addWidget(error_label)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Annulla")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Rinomina")
        
        def on_rename():
            new_name = name_input.text().strip()
            
            if not new_name:
                error_label.setText("Il nome non può essere vuoto")
                return
            
            if new_name == old_name:
                dialog.accept()
                return
            
            # Verifica che il nome non sia già in uso
            existing_cols = [col[1] for col in columns]
            if new_name in existing_cols:
                error_label.setText(f"Nome '{new_name}' già esistente")
                return
            
            # Esegui il rename
            if self.db_manager.rename_column(self.current_table, old_name, new_name):
                self.refresh_table_data()
                QMessageBox.information(
                    self,
                    "Successo",
                    f"Colonna rinominata da '{old_name}' a '{new_name}'"
                )
                dialog.accept()
            else:
                error_label.setText("Errore durante il rename")
        
        ok_btn.clicked.connect(on_rename)
        name_input.returnPressed.connect(on_rename)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        
        dialog.exec()