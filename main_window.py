# llm_context_builder/main_window.py

import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QCheckBox, QLineEdit,
    QStatusBar, QToolBar, QTextEdit # Added QTextEdit for optional preview
)
from PySide6.QtGui import QAction, QIcon, QKeySequence, QDesktopServices, QClipboard
from PySide6.QtCore import Qt, Slot, QSettings, QUrl

# Import custom widgets and functions
from .file_tree_widget import FileTreeWidget # Corrected import name
from .file_processor import generate_context_file

# --- Application Settings ---
ORG_NAME = "MyCompany" # Or your name/handle
APP_NAME = "LLMContextBuilder"
SETTINGS_OUTPUT_PATH = "lastOutputPath"
SETTINGS_COPY_CLIPBOARD = "copyToClipboard"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - Context Generator")
        self.setGeometry(100, 100, 800, 600) # x, y, width, height

        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.current_project_dir = None
        self.output_file_path = None

        # --- Central Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Directory Selection Area ---
        dir_layout = QHBoxLayout()
        self.select_dir_button = QPushButton("Select Project Directory...")
        self.select_dir_button.setIcon(QIcon.fromTheme("folder-open"))
        self.dir_label = QLabel("No project directory selected.")
        self.dir_label.setStyleSheet("font-style: italic; color: grey;")
        dir_layout.addWidget(self.select_dir_button)
        dir_layout.addWidget(self.dir_label, 1) # Stretch label
        main_layout.addLayout(dir_layout)

        # --- File Tree ---
        self.file_tree = FileTreeWidget() # Use the custom widget
        main_layout.addWidget(self.file_tree, 1) # Tree takes most space

        # --- Output Configuration Area ---
        output_layout = QHBoxLayout()
        self.select_output_button = QPushButton("Output File...")
        self.select_output_button.setIcon(QIcon.fromTheme("document-save-as"))
        self.output_path_display = QLineEdit()
        self.output_path_display.setPlaceholderText("Select output file location...")
        self.output_path_display.setReadOnly(True) # Prevent manual editing
        output_layout.addWidget(self.select_output_button)
        output_layout.addWidget(self.output_path_display, 1)
        main_layout.addLayout(output_layout)

        # --- Options and Action Area ---
        action_layout = QHBoxLayout()
        self.copy_clipboard_checkbox = QCheckBox("Copy content to clipboard")
        self.generate_button = QPushButton("Generate Context File")
        self.generate_button.setIcon(QIcon.fromTheme("document-save"))
        self.generate_button.setStyleSheet("font-weight: bold;")
        action_layout.addWidget(self.copy_clipboard_checkbox)
        action_layout.addStretch()
        action_layout.addWidget(self.generate_button)
        main_layout.addLayout(action_layout)

        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready.")

        # --- Optional: Output Preview Area ---
        # self.preview_area = QTextEdit()
        # self.preview_area.setReadOnly(True)
        # self.preview_area.setPlaceholderText("Generated content will appear here (if enabled)...")
        # main_layout.addWidget(self.preview_area, 1) # Add preview area

        # --- Load Settings ---
        self._load_settings()

        # --- Connect Signals ---
        self.select_dir_button.clicked.connect(self.select_project_directory)
        self.select_output_button.clicked.connect(self.select_output_file)
        self.generate_button.clicked.connect(self.generate_output)
        # Update settings when checkbox state changes
        self.copy_clipboard_checkbox.stateChanged.connect(self._save_settings)


    # --- Action Methods ---

    @Slot()
    def select_project_directory(self):
        """Opens a dialog to select the root project directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Project Root Directory",
            # Start from home directory or last used? For now, let's use home.
            os.path.expanduser("~")
        )
        if directory:
            self.current_project_dir = os.path.abspath(directory)
            self.dir_label.setText(f"Project: {self.current_project_dir}")
            self.dir_label.setStyleSheet("") # Reset style
            self.statusBar.showMessage(f"Loading directory: {self.current_project_dir}...")
            QApplication.processEvents() # Allow UI to update
            self.file_tree.populate_tree(self.current_project_dir)
            self.statusBar.showMessage(f"Directory loaded: {self.current_project_dir}", 5000) # 5 seconds
            self.generate_button.setEnabled(True) # Enable generation only after dir selected
        else:
             self.statusBar.showMessage("Directory selection cancelled.", 3000)

    @Slot()
    def select_output_file(self):
        """Opens a dialog to select the output .txt file path."""
        # Suggest a default filename based on the project dir if possible
        default_name = "llm_context.txt"
        if self.current_project_dir:
            project_name = os.path.basename(self.current_project_dir)
            default_name = f"{project_name}_context.txt"

        # Start dialog in the directory of the last saved file, or home
        start_dir = os.path.dirname(self.output_file_path) if self.output_file_path else os.path.expanduser("~")
        suggested_path = os.path.join(start_dir, default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Context File As",
            suggested_path,
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            # Ensure it has a .txt extension if none provided
            if not file_path.lower().endswith(".txt"):
                file_path += ".txt"

            self.output_file_path = os.path.abspath(file_path)
            self.output_path_display.setText(self.output_file_path)
            self._save_settings() # Save the newly selected path

            # --- Warning if saving inside project directory ---
            if self.current_project_dir and self.output_file_path.startswith(self.current_project_dir):
                QMessageBox.warning(
                    self,
                    "Output Location Warning",
                    "Saving the output file inside the selected project directory is "
                    "generally not recommended, as it might be included in future "
                    "context generations.\n\nConsider saving it elsewhere.",
                    QMessageBox.StandardButton.Ok
                )
            self.statusBar.showMessage(f"Output file set to: {self.output_file_path}", 5000)
        else:
            self.statusBar.showMessage("Output file selection cancelled.", 3000)

    @Slot()
    def generate_output(self):
        """Gathers selections, processes files, and generates the output."""
        if not self.current_project_dir:
            QMessageBox.warning(self, "Error", "Please select a project directory first.")
            return

        if not self.output_file_path:
            # If no output path specifically selected, prompt the user now
            self.statusBar.showMessage("Please select an output file location.", 3000)
            self.select_output_file()
            if not self.output_file_path: # If still no path after prompt, cancel
                 return

        selected_files = self.file_tree.get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please check the files or folders you want to include.")
            return

        # --- Overwrite Confirmation ---
        if os.path.exists(self.output_file_path):
            reply = QMessageBox.question(
                self,
                "Confirm Overwrite",
                f"The output file already exists:\n{self.output_file_path}\n\nDo you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No # Default to No
            )
            if reply == QMessageBox.StandardButton.No:
                self.statusBar.showMessage("Generation cancelled by user.", 3000)
                return

        self.statusBar.showMessage("Generating context file...")
        self.generate_button.setEnabled(False) # Disable button during processing
        QApplication.processEvents()

        # --- Call the Processor ---
        success, result = generate_context_file(
            selected_files,
            self.output_file_path,
            self.current_project_dir
        )

        self.generate_button.setEnabled(True) # Re-enable button

        # --- Handle Result ---
        if success:
            generated_content, user_message = result
            self.statusBar.showMessage("Context file generated successfully!", 5000)
            QMessageBox.information(self, "Success", user_message)

            # --- Optional Preview ---
            # self.preview_area.setPlainText(generated_content)

            # --- Copy to Clipboard ---
            if self.copy_clipboard_checkbox.isChecked():
                try:
                    clipboard = QApplication.clipboard()
                    clipboard.setText(generated_content)
                    self.statusBar.showMessage("Content copied to clipboard!", 5000)
                    # Optionally add to the success message box?
                    # QMessageBox.information(self, "Success", user_message + "\n\nContent copied to clipboard.")
                except Exception as e:
                     QMessageBox.warning(self, "Clipboard Error", f"Could not copy to clipboard: {e}")
                     self.statusBar.showMessage("File generated, but failed to copy to clipboard.", 5000)

            # --- Optionally Open Containing Folder ---
            reply = QMessageBox.question(
                 self,
                 "Open Output Location?",
                 "Context file generated successfully.\n\nDo you want to open the folder containing the output file?",
                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                 QMessageBox.StandardButton.No
             )
            if reply == QMessageBox.StandardButton.Yes:
                 output_dir = os.path.dirname(self.output_file_path)
                 try:
                     # Use QDesktopServices for cross-platform opening
                     QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))
                 except Exception as e:
                     QMessageBox.warning(self, "Error", f"Could not open folder: {e}")


        else:
            error_message = result
            self.statusBar.showMessage("Error generating context file.", 5000)
            QMessageBox.critical(self, "Generation Failed", f"An error occurred:\n{error_message}")


    # --- Settings Persistence ---

    def _load_settings(self):
        """Load saved settings on startup."""
        # Load last output path
        saved_path = self.settings.value(SETTINGS_OUTPUT_PATH)
        if saved_path and isinstance(saved_path, str):
            # Basic validation: check if the directory still exists
            if os.path.exists(os.path.dirname(saved_path)):
                 self.output_file_path = saved_path
                 self.output_path_display.setText(self.output_file_path)
            else:
                 print(f"Warning: Saved output directory no longer exists: {os.path.dirname(saved_path)}")
                 self.settings.remove(SETTINGS_OUTPUT_PATH) # Remove invalid setting

        # Load clipboard preference
        copy_pref = self.settings.value(SETTINGS_COPY_CLIPBOARD, True, type=bool) # Default True
        self.copy_clipboard_checkbox.setChecked(copy_pref)

        # Initially disable generate button until a directory is loaded
        self.generate_button.setEnabled(False)


    def _save_settings(self):
        """Save current settings."""
        if self.output_file_path:
            self.settings.setValue(SETTINGS_OUTPUT_PATH, self.output_file_path)
        self.settings.setValue(SETTINGS_COPY_CLIPBOARD, self.copy_clipboard_checkbox.isChecked())

    def closeEvent(self, event):
        """Save settings when closing the application."""
        self._save_settings()
        super().closeEvent(event)