import re
from typing import Tuple
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import QDate


class InputValidator:
    @staticmethod
    def validate_text(value: str, min_length: int = 0, max_length: int = 500) -> Tuple[bool, str]:
        if not value and min_length > 0:
            return False, f"Minimum {min_length} characters required"
        if len(value) > max_length:
            return False, f"Maximum {max_length} characters allowed"
        return True, ""
    
    @staticmethod
    def validate_number(value: str) -> Tuple[bool, str]:
        if not value:
            return False, "Number required"
        try:
            float(value)
            return True, ""
        except ValueError:
            return False, "Invalid number format"
    
    @staticmethod
    def validate_date(value: str) -> Tuple[bool, str]:
        if not value:
            return False, "Date required"
        try:
            QDate.fromString(value, "yyyy-MM-dd")
            if not QDate.fromString(value, "yyyy-MM-dd").isValid():
                return False, "Invalid date. Use YYYY-MM-DD format"
            return True, ""
        except:
            return False, "Invalid date format"
    
    @staticmethod
    def validate_email(value: str) -> Tuple[bool, str]:
        if not value:
            return True, ""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_regex, value):
            return True, ""
        return False, "Invalid email format"
    
    @staticmethod
    def restrict_input(line_edit: QLineEdit, pattern: str):
        def on_text_changed(text):
            filtered = ''.join(c for c in text if re.match(pattern, c))
            if filtered != text:
                line_edit.blockSignals(True)
                line_edit.setText(filtered)
                line_edit.blockSignals(False)
        line_edit.textChanged.connect(on_text_changed)
    
    @staticmethod
    def restrict_number_input(line_edit: QLineEdit):
        def on_text_changed(text):
            if not text:
                return
            filtered = ''.join(c for c in text if c.isdigit() or c == '.')
            if filtered.count('.') > 1:
                filtered = filtered[:filtered.rfind('.')] + filtered[filtered.rfind('.')+1:].replace('.', '')
            if filtered != text:
                line_edit.blockSignals(True)
                line_edit.setText(filtered)
                line_edit.blockSignals(False)
        line_edit.textChanged.connect(on_text_changed)
