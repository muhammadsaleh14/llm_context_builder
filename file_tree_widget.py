# llm_context_builder/file_tree_widget.py

import os
import sys # Import sys for path manipulation
from PySide6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QApplication,
                               QTreeWidgetItemIterator)
from PySide6.QtCore import Qt, Slot, QDir
from PySide6.QtGui import QIcon, QFont, QColor # Added QColor for error text

from llm_context_builder.file_processor import DEFAULT_IGNORE_PATTERNS, should_ignore

# --- Helper Function to get resource path ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as a bundled app, use the directory of this script file
        base_path = os.path.dirname(os.path.abspath(__file__)) # Use directory of file_tree_widget.py
    return os.path.join(base_path, relative_path)

# --- Define Icon Paths Using resource_path ---
ICON_FOLDER_PATH = resource_path("icons/folder.png")
ICON_FILE_PATH = resource_path("icons/file.png")


class FileTreeWidget(QTreeWidget):
    """
    A QTreeWidget subclass to display a directory structure with checkboxes
    and handle hierarchical selection.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Load Icons using absolute paths ---
        try:
            # Try loading from theme first
            self.icon_folder = QIcon.fromTheme("folder")
            self.icon_file = QIcon.fromTheme("text-x-generic")

            # If theme icons are null (not found), try loading from files
            if self.icon_folder.isNull():
                print(f"Theme icon 'folder' not found, trying file: {ICON_FOLDER_PATH}")
                self.icon_folder = QIcon(ICON_FOLDER_PATH)

            if self.icon_file.isNull():
                print(f"Theme icon 'text-x-generic' not found, trying file: {ICON_FILE_PATH}")
                self.icon_file = QIcon(ICON_FILE_PATH)

            # Final check: If still null after trying files, raise error to fallback
            if self.icon_folder.isNull() or self.icon_file.isNull():
                 # Check if the files actually exist for better debugging
                 folder_exists = os.path.exists(ICON_FOLDER_PATH)
                 file_exists = os.path.exists(ICON_FILE_PATH)
                 raise RuntimeError(f"Failed to load icons. Exists? Folder: {folder_exists}, File: {file_exists}")

        except Exception as e:
            print(f"Warning: Could not load custom/file icons ({e}). Falling back to system style.")
            style = QApplication.style()
            self.icon_folder = style.standardIcon(style.StandardPixmap.SP_DirIcon)
            self.icon_file = style.standardIcon(style.StandardPixmap.SP_FileIcon)
        # --- End Icon Loading ---


        self.setHeaderLabel("Project Files")
        self.setColumnCount(1)
        self.project_root = None
        self._ignore_patterns = DEFAULT_IGNORE_PATTERNS.copy() # Use a copy

        self.itemChanged.connect(self._handle_item_changed)
        self._is_changing_programmatically = False

        # font = QFont("monospace") # Optional monospace font
        # self.setFont(font)


    def set_ignore_patterns(self, patterns):
        """Set the patterns to ignore when populating the tree."""
        self._ignore_patterns = set(patterns)
        if self.project_root:
            self.populate_tree(self.project_root) # Repopulate if needed

    def get_ignore_patterns(self):
        """Get the current set of ignore patterns."""
        return self._ignore_patterns

    # --- THIS METHOD WAS LIKELY MISSING OR MISPLACED ---
    @Slot(str)
    def populate_tree(self, directory_path):
        """
        Populates the tree widget with the contents of the given directory.
        """
        self.clear() # Clear existing items
        self.project_root = os.path.abspath(directory_path)
        if not os.path.isdir(self.project_root):
            print(f"Error: Path is not a valid directory: {self.project_root}")
            # Optionally display an error item in the tree
            error_item = QTreeWidgetItem(self, ["Error: Not a valid directory"])
            error_item.setForeground(0, QColor("red"))
            self.project_root = None
            return

        self._is_changing_programmatically = True
        try:
            # Add root item representing the selected directory itself
            root_display_name = os.path.basename(self.project_root) # Show only folder name
            root_item = self._add_item(None, self.project_root, is_dir=True, display_name=root_display_name)
            root_item.setExpanded(True) # Expand the root node by default
            # Populate children *of* the root directory
            self._populate_recursive(self.project_root, root_item)

        finally:
            self._is_changing_programmatically = False

        # Set initial state after population and signal enabling
        # Use invisibleRootItem() to affect the top-level items added
        self._set_check_state_recursive(self.invisibleRootItem(), Qt.CheckState.Checked)


    def _populate_recursive(self, directory_path, parent_item):
        """Helper function to recursively populate the tree."""
        try:
            entries = os.listdir(directory_path)
        except OSError as e:
            print(f"Warning: Could not access {directory_path}: {e}")
            error_item = QTreeWidgetItem(parent_item, [f"Error accessing folder content"])
            error_item.setForeground(0, QColor("red")) # Use QColor
            error_item.setFlags(error_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            return # Stop descent here

        for entry in sorted(entries):
            full_path = os.path.join(directory_path, entry)

            if should_ignore(entry, self._ignore_patterns):
                continue

            is_dir = os.path.isdir(full_path)
            is_file = os.path.isfile(full_path) # Check if it's actually a file

            if is_dir:
                dir_item = self._add_item(parent_item, full_path, is_dir=True)
                self._populate_recursive(full_path, dir_item) # Recurse
            elif is_file:
                self._add_item(parent_item, full_path, is_dir=False)
            # Silently ignore other types (symlinks, etc.) for now


    # Added display_name parameter for flexibility (e.g., for root item)
    def _add_item(self, parent, path, is_dir, display_name=None):
        """Adds an item to the tree, setting flags and data."""
        if display_name is None:
            display_name = os.path.basename(path)

        # Determine the parent for the new item
        tree_parent = parent if parent else self # Add to tree root if parent is None

        item = QTreeWidgetItem(tree_parent)
        item.setText(0, display_name)
        item.setData(0, Qt.ItemDataRole.UserRole, path) # Store full path
        item.setData(1, Qt.ItemDataRole.UserRole, is_dir) # Store type

        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
        # Don't set check state here - let the final step in populate_tree handle it

        item.setIcon(0, self.icon_folder if is_dir else self.icon_file)

        # Tooltip shows the full path
        item.setToolTip(0, path)

        return item


    @Slot(QTreeWidgetItem, int)
    def _handle_item_changed(self, item, column):
        """Handles changes to item check states, implementing hierarchy."""
        # Check if the change is relevant (column 0) and not programmatically triggered within this handler
        if column == 0 and not self._is_changing_programmatically:
            self._is_changing_programmatically = True  # Prevent infinite recursion
            try:
                current_check_state = item.checkState(0) # Get the state *after* the change
                is_dir = item.data(1, Qt.ItemDataRole.UserRole)

                # --- Propagate check state downwards ONLY if it's a directory
                # --- AND the state change was to fully Checked or Unchecked.
                # --- Do NOT propagate if the state became PartiallyChecked, as this
                # --- usually happens because a child changed, not a direct user click
                # --- on the directory checkbox with the intent to check/uncheck all.
                if is_dir and current_check_state != Qt.CheckState.PartiallyChecked:
                    # User explicitly checked or unchecked the directory item itself.
                    # Apply this state to all checkable children recursively.
                    self._set_check_state_recursive_children_only(item, current_check_state)

                # --- Always update the parent's state based on children states ---
                # This needs to happen regardless of whether the current item is a file or directory,
                # or whether downward propagation occurred.
                self._update_parent_state(item.parent())

            finally:
                self._is_changing_programmatically = False # Release the lock

    # ... (rest of the class, including _set_check_state_recursive_children_only and _update_parent_state) ...



    def _set_check_state_recursive(self, parent_item, state):
        """Recursively set the check state, starting from parent_item (can be root)."""
        # Handle the invisible root item passed from populate_tree
        if parent_item == self.invisibleRootItem():
            for i in range(self.topLevelItemCount()):
                child = self.topLevelItem(i)
                if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                     if child.checkState(0) != state:
                         child.setCheckState(0, state)
                     # Recurse only if it's a directory
                     if child.data(1, Qt.ItemDataRole.UserRole):
                         self._set_check_state_recursive_children_only(child, state)
        elif parent_item: # Handle regular items passed from _handle_item_changed
             if parent_item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                  if parent_item.checkState(0) != state:
                       parent_item.setCheckState(0, state)
                  # Apply to children only if it's a directory
                  if parent_item.data(1, Qt.ItemDataRole.UserRole):
                      self._set_check_state_recursive_children_only(parent_item, state)


    def _set_check_state_recursive_children_only(self, parent_item, state):
         """Helper to apply state only to children, avoids re-applying to parent"""
         if not parent_item: return # Safety check

         for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                current_state = child.checkState(0)
                # Only set state if it's different, prevents unnecessary signals/recursion
                if current_state != state:
                    child.setCheckState(0, state) # This might trigger _handle_item_changed if user interacts

                # Still need to recurse for grandchildren if the child is a directory,
                # even if the child's state didn't change itself.
                if child.data(1, Qt.ItemDataRole.UserRole):
                    self._set_check_state_recursive_children_only(child, state)


    def _update_parent_state(self, parent_item):
        """Updates the parent's check state based on its children."""
        if not parent_item or parent_item == self.invisibleRootItem():
            return # Stop at the root or if no parent

        checked_count = 0
        unchecked_count = 0
        partially_checked_count = 0
        total_checkable_children = 0

        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                total_checkable_children += 1
                state = child.checkState(0)
                if state == Qt.CheckState.Checked:
                    checked_count += 1
                elif state == Qt.CheckState.Unchecked:
                    unchecked_count += 1
                else: # PartiallyChecked
                    partially_checked_count += 1

        new_state = Qt.CheckState.PartiallyChecked # Default
        if total_checkable_children == 0:
             # No checkable children, maybe keep parent state? Or default to checked?
             # Let's default to Checked as it's the initial state.
             new_state = Qt.CheckState.Checked
        elif partially_checked_count > 0:
            new_state = Qt.CheckState.PartiallyChecked
        elif checked_count == total_checkable_children:
            new_state = Qt.CheckState.Checked
        elif unchecked_count == total_checkable_children:
            new_state = Qt.CheckState.Unchecked
        # Else, it remains PartiallyChecked (mix of checked/unchecked)

        if parent_item.checkState(0) != new_state:
             parent_item.setCheckState(0, new_state)
             # No need for explicit recursion up, signal/slot handles parent update


    def get_selected_files(self):
        """
        Returns a list of absolute paths for all *checked* files.
        """
        selected = []
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            is_dir = item.data(1, Qt.ItemDataRole.UserRole)
            check_state = item.checkState(0)

            # Only include files that are explicitly checked
            if not is_dir and check_state == Qt.CheckState.Checked:
                 path = item.data(0, Qt.ItemDataRole.UserRole)
                 if path and isinstance(path, str):
                     selected.append(path)
                 else:
                     print(f"Warning: Checked file item '{item.text(0)}' lacks valid path data.")

            iterator += 1
        return selected