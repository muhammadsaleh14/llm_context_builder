# llm_context_builder/file_processor.py

import os
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration for ignored items ---
# Common directories/files to ignore by default (can be customized)
DEFAULT_IGNORE_PATTERNS = {
    ".git", "__pycache__", ".vscode", ".idea", "node_modules", "venv",
    ".DS_Store", "*.pyc", "*.log", "*.tmp", "*.swp"
}
# Common binary file extensions to skip reading content
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.tif', '.tiff',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.exe', '.dll', '.so', '.dylib', '.app',
    '.o', '.a', '.lib',
    '.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov', '.wmv',
    '.db', '.sqlite', '.sqlite3'
}

def is_likely_binary(filepath):
    """Check if a file is likely binary based on its extension."""
    _, ext = os.path.splitext(filepath)
    return ext.lower() in BINARY_EXTENSIONS

def should_ignore(name, ignore_patterns):
    """Check if a file/directory name matches any ignore pattern."""
    if name in ignore_patterns:
        return True
    # Basic wildcard matching (e.g., *.log)
    for pattern in ignore_patterns:
        if pattern.startswith("*.") and name.endswith(pattern[1:]):
            return True
    return False


def generate_context_file(selected_files, output_path, project_root):
    """
    Reads content from selected files and writes it to the output file.

    Args:
        selected_files (list): A list of absolute paths to the files to include.
        output_path (str): The absolute path for the output text file.
        project_root (str): The absolute path of the project root directory.

    Returns:
        tuple: (success (bool), message/content (str))
               If success is True, message is the concatenated content.
               If success is False, message is an error description.
    """
    all_content = []
    file_count = 0
    errors = []

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            logging.info(f"Created output directory: {output_dir}")
        except OSError as e:
            error_msg = f"Error creating output directory {output_dir}: {e}"
            logging.error(error_msg)
            return False, error_msg

    try:
        with open(output_path, 'w', encoding='utf-8', errors='ignore') as outfile:
            for file_path in sorted(selected_files): # Sort for consistent order
                relative_path = os.path.relpath(file_path, project_root)
                logging.info(f"Processing: {relative_path}")

                if not os.path.exists(file_path):
                    logging.warning(f"Skipping non-existent file: {relative_path}")
                    errors.append(f"Skipped non-existent file: {relative_path}")
                    continue

                if is_likely_binary(file_path):
                    logging.info(f"Skipping likely binary file: {relative_path}")
                    # Optionally add a note about the binary file instead of skipping silently
                    separator = f"\n--- File: {relative_path} (Binary file, content skipped) ---\n"
                    outfile.write(separator)
                    all_content.append(separator)
                    continue # Skip reading binary files

                separator = f"\n--- File: {relative_path} ---\n\n"
                outfile.write(separator)
                all_content.append(separator)

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        content = infile.read()
                        outfile.write(content + "\n") # Add newline after content
                        all_content.append(content + "\n")
                        file_count += 1
                except Exception as e:
                    error_msg = f"Error reading {relative_path}: {e}"
                    logging.error(error_msg)
                    errors.append(error_msg)
                    outfile.write(f"*** Error reading file: {e} ***\n")
                    all_content.append(f"*** Error reading file: {e} ***\n")

        final_content = "".join(all_content)
        success_msg = f"Successfully generated context file at:\n{output_path}\n\nProcessed {file_count} text files."
        if errors:
            success_msg += "\n\nEncountered some issues:\n- " + "\n- ".join(errors)
        logging.info(f"Finished generating {output_path}. Processed {file_count} files.")
        return True, (final_content, success_msg) # Return content and user message

    except IOError as e:
        error_msg = f"Error writing to output file {output_path}: {e}"
        logging.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred during generation: {e}"
        logging.exception(error_msg) # Log full traceback
        return False, error_msg