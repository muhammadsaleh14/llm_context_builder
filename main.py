# llm_context_builder/main.py

import sys
from PySide6.QtWidgets import QApplication
from .main_window import MainWindow # Corrected import name

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Optional: Set application details for QSettings
    # app.setOrganizationName("MyCompany") # Match in MainWindow
    # app.setApplicationName("LLMContextBuilder") # Match in MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())