from typing import Optional, Tuple
from PyQt6.QtWidgets import QLineEdit, QStyledItemDelegate
from PyQt6.QtCore import Qt, QDate, QRect, QSize
from PyQt6.QtGui import QTextDocument, QPalette, QTextCursor, QTextCharFormat

from validators import InputValidator


class EditableTableDelegate(QStyledItemDelegate):
    def __init__(self, db_manager=None, table_name=None):
        super().__init__()
        self.db_manager = db_manager
        self.table_name = table_name
    
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        
        if self.db_manager and self.table_name and index.column() >= 0:
            columns = self.db_manager.get_columns(self.table_name)
            if index.column() < len(columns):
                col_name = columns[index.column()][1]
                col_type = columns[index.column()][2]
                spec_type = self.db_manager.get_special_type(self.table_name, col_name)
                spec_type_name = spec_type[0] if spec_type else None
                
                if spec_type_name == "DATE":
                    editor.setPlaceholderText("yyyy-MM-dd")
                elif col_type == "REAL":
                    InputValidator.restrict_number_input(editor)
                else:
                    InputValidator.restrict_input(editor, r'^[a-zA-Z0-9\s\-._@]*$')
        
        editor.returnPressed.connect(lambda: self.commitData.emit(editor))
        return editor
    
    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        # Apply desanitization for display
        display_value = InputValidator.desanitize_text(str(value)) if value else ""
        editor.setText(display_value)
    
    def setModelData(self, editor, model, index):
        value = editor.text()
        
        if self.db_manager and self.table_name and index.column() >= 0:
            columns = self.db_manager.get_columns(self.table_name)
            if index.column() < len(columns):
                col_name = columns[index.column()][1]
                col_type = columns[index.column()][2]
                spec_type = self.db_manager.get_special_type(self.table_name, col_name)
                spec_type_name = spec_type[0] if spec_type else None
                
                if spec_type_name == "DATE":
                    if not self._validate_date(value):
                        return
                elif col_type == "REAL":
                    if not self._validate_number(value):
                        return
        
        # Sanitize the value before saving
        sanitized_value = InputValidator.sanitize_text(value)
        model.setData(index, sanitized_value, Qt.ItemDataRole.EditRole)
        
        if self.db_manager and self.table_name and index.column() > 0:
            id_index = model.index(index.row(), 0)
            record_id = model.data(id_index, Qt.ItemDataRole.UserRole)
            if record_id is not None:
                columns = self.db_manager.get_columns(self.table_name)
                if index.column() < len(columns):
                    col_name = columns[index.column()][1]
                    self.db_manager.update_record(
                        self.table_name, 
                        record_id, 
                        {col_name: sanitized_value}
                    )
    
    def _validate_date(self, value: str) -> bool:
        if not value:
            return True
        try:
            date = QDate.fromString(value, "yyyy-MM-dd")
            return date.isValid()
        except:
            return False
    
    def _validate_number(self, value: str) -> bool:
        if not value:
            return True
        try:
            float(value)
            return True
        except:
            return False
    
    def paint(self, painter, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text:
            painter.save()
            
            doc = QTextDocument()
            # Desanitize text for proper display and convert newlines to HTML breaks
            display_text = InputValidator.desanitize_text(str(text))
            # Re-escape for safe HTML rendering in QTextDocument
            html_text = display_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            doc.setHtml(html_text)
            doc.setTextWidth(option.rect.width() - 4)
            
            fg_color = option.palette.color(QPalette.ColorRole.Text)
            cursor = QTextCursor(doc)
            cursor.select(QTextCursor.SelectionType.Document)
            fmt = QTextCharFormat()
            fmt.setForeground(fg_color)
            cursor.mergeCharFormat(fmt)
            
            painter.translate(option.rect.left() + 2, option.rect.top() + 2)
            doc.drawContents(painter)
            
            painter.restore()
        else:
            super().paint(painter, option, index)
    
    def sizeHint(self, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text:
            doc = QTextDocument()
            # Desanitize text for proper size calculation and convert newlines to HTML breaks
            display_text = InputValidator.desanitize_text(str(text))
            html_text = display_text.replace('\n', '<br>')
            doc.setHtml(html_text)
            doc.setTextWidth(option.rect.width() - 4 if option.rect.width() > 4 else 150)
            return QSize(int(doc.idealWidth()), int(doc.size().height()) + 4)
        return super().sizeHint(option, index)
