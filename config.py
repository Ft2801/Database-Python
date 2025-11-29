import os
import json
from typing import Dict

THEMES = {
    "Elegant Dark": {
        "bg": "#0f1419",
        "fg": "#e0e0e0",
        "primary": "#6366f1",
        "primary_dark": "#4f46e5",
        "accent": "#ec4899",
        "success": "#10b981",
        "danger": "#ef4444",
        "warning": "#f59e0b",
        "card_bg": "#1a1f2e",
        "header_bg": "#0d0f14",
        "border": "#2d3748",
        "hover": "#7c3aed",
        "input_bg": "#1a1f2e",
    },
    "Clean White": {
        "bg": "#ffffff",
        "fg": "#000000",
        "primary": "#3b82f6",
        "primary_dark": "#2563eb",
        "accent": "#f472b6",
        "success": "#22c55e",
        "danger": "#ef4444",
        "warning": "#eab308",
        "card_bg": "#f9fafb",
        "header_bg": "#f3f4f6",
        "border": "#d1d5db",
        "hover": "#60a5fa",
        "input_bg": "#ffffff",
    },
}


class StyleManager:
    def __init__(self):
        self.current_theme = "Elegant Dark"
        self.colors = THEMES[self.current_theme].copy()
    
    def set_theme(self, theme_name: str):
        if theme_name in THEMES:
            self.current_theme = theme_name
            self.colors = THEMES[theme_name].copy()
    
    def get_stylesheet(self) -> str:
        return f"""
        QMainWindow, QDialog, QWidget {{
            background-color: {self.colors['bg']};
            color: {self.colors['fg']};
        }}
        QLabel {{
            color: {self.colors['fg']};
        }}
        
        QPushButton {{
            background-color: {self.colors['primary']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            font-size: 10pt;
        }}
        
        QPushButton:hover {{
            background-color: {self.colors['hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {self.colors['primary_dark']};
        }}
        
        QPushButton:disabled {{
            background-color: {self.colors['border']};
            color: {self.colors['fg']};
        }}
        
        QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {{
            background-color: {self.colors['input_bg']};
            color: {self.colors['fg']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
            padding: 6px;
            font-size: 10pt;
        }}
        
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
            border: 2px solid {self.colors['primary']};
            background-color: {self.colors['input_bg']};
        }}
        
        QCalendarWidget {{
            background-color: {self.colors['card_bg']};
            color: {self.colors['fg']};
        }}
        
        QCalendarWidget QWidget {{
            color: {self.colors['fg']};
        }}
        
        QCalendarWidget QAbstractItemView {{
            background-color: {self.colors['input_bg']};
            selection-background-color: {self.colors['primary']};
        }}
        
        QTableWidget {{
            background-color: {self.colors['card_bg']};
            color: {self.colors['fg']};
            gridline-color: {self.colors['border']};
            border: 1px solid {self.colors['border']};
        }}
        
        QTableWidget::item {{
            padding: 4px;
            color: {self.colors['fg']};
        }}
        
        QTableWidget::item:selected {{
            background-color: {self.colors['primary']};
            color: white;
        }}
        
        QHeaderView::section {{
            background-color: {self.colors['header_bg']};
            color: {self.colors['fg']};
            padding: 6px;
            border: none;
            border-right: 1px solid {self.colors['border']};
            font-weight: bold;
        }}
        
        QListWidget {{
            background-color: {self.colors['card_bg']};
            color: {self.colors['fg']};
            border: 1px solid {self.colors['border']};
            border-radius: 4px;
        }}
        
        QListWidget::item:selected {{
            background-color: {self.colors['primary']};
        }}
        
        QFrame {{
            background-color: {self.colors['bg']};
            border: none;
        }}
        
        QScrollBar:vertical {{
            background-color: {self.colors['card_bg']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {self.colors['primary']};
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {self.colors['hover']};
        }}
        
        QComboBox::drop-down {{
            border: none;
        }}
        
        QComboBox::down-arrow {{
            image: none;
        }}
        
        QStatusBar {{
            background-color: {self.colors['header_bg']};
            color: {self.colors['fg']};
            border-top: 1px solid {self.colors['border']};
        }}
        """


class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.data = self.load()
    
    def load(self) -> Dict:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"theme": "Elegant Dark"}
    
    def save(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.data, f)
    
    def get(self, key: str, default=None):
        return self.data.get(key, default)
    
    def set(self, key: str, value):
        self.data[key] = value
        self.save()
