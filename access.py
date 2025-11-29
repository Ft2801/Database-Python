import sys
from PyQt6.QtWidgets import QApplication

from app import ModernDBApp


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernDBApp()
    window.show()
    sys.exit(app.exec())
