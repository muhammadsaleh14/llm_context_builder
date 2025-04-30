# llm_context_builder/main.py

import sys
import os


from PySide6.QtWidgets import QApplication
# Changed from relative to absolute package import
from llm_context_builder.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Optional: Set application details for QSettings
    # app.setOrganizationName("MyCompany") # Match in MainWindow
    # app.setApplicationName("LLMContextBuilder") # Match in MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())