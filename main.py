# llm_context_builder/main.py

import sys
import os

# --- START sys.path modification ---
# Add the parent directory (containing llm_context_builder) to sys.path
# This allows running 'python llm_context_builder/main.py' from the parent directory
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    # Insert at position 0 to prioritize project imports
    sys.path.insert(0, parent_dir)
# --- END sys.path modification ---

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