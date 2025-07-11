import os
from pathlib import Path

# Application Name
APP_NAME = "DesktopNotes"
APP_ID = "org.kde.plasma.desktopnotes" # Matches metadata.json

# Base paths
HOME_DIR = Path.home()
CONFIG_DIR = HOME_DIR / ".config" / "desktop-notes"
DATA_DIR = HOME_DIR / ".local" / "share" / "desktop-notes"

# Ensure directories exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# File paths
SETTINGS_FILE = CONFIG_DIR / "settings.ini"
DATABASE_FILE = DATA_DIR / "notes.db"

# Default editor command
# This should be configurable via settings.ini in the future
DEFAULT_EDITOR_COMMAND = "konsole -e nvim {filepath}" # Placeholder, nvim might not be installed

# Note Widget Defaults
DEFAULT_NOTE_WIDTH = 250
DEFAULT_NOTE_HEIGHT = 150
DEFAULT_NOTE_TRANSPARENCY = 0.85  # 0.0 (transparent) to 1.0 (opaque)
DEFAULT_NOTE_BG_COLOR = "#FFFFE0"  # Light yellow, similar to sticky notes
DEFAULT_NOTE_MARGIN = 10  # Pixels

# Placeholder text for new notes
PLACEHOLDER_TEXT = "Select File..."
PLACEHOLDER_FONT_SIZE_PT = 22

# Drag/Resize mode visual cue
DRAG_RESIZE_BORDER_COLOR = "yellow"
DRAG_RESIZE_BORDER_WIDTH = 3  # Pixels

# New note placement offset (e.g., when using "Add New Note" from context menu)
NEW_NOTE_OFFSET_X = 30
NEW_NOTE_OFFSET_Y = 30

# Database table and column names
DB_TABLE_NOTES = "notes"
DB_COL_ID = "id"
DB_COL_STATUS = "status" # "shown" or "hidden"
DB_COL_FILEPATH = "filepath"
DB_COL_POS_X = "position_x"
DB_COL_POS_Y = "position_y"
DB_COL_SIZE_W = "size_width"
DB_COL_SIZE_H = "size_height"
DB_COL_STYLE_TRANSPARENCY = "style_transparency"
DB_COL_STYLE_BG_COLOR = "style_backgroundColor"
DB_COL_STYLE_MARGIN = "style_margin"

# Status values
NOTE_STATUS_SHOWN = "shown"
NOTE_STATUS_HIDDEN = "hidden"

# File types
SUPPORTED_FILE_TYPES_FILTER = "Text and Markdown files (*.txt *.md);;All files (*)"

# Minimum size for a note widget
MIN_NOTE_WIDTH = 50
MIN_NOTE_HEIGHT = 30

# Maximum values for styling
MAX_MARGIN = 50 # Arbitrary practical maximum for margin slider

# Default text editor command (future setting)
DEFAULT_TEXT_EDITOR_CMD_PATTERN = "kate {filepath}" # Using kate as a more common KDE default

# --- For settings.ini (QSettings) ---
# Group names
SETTINGS_GROUP_GENERAL = "General"

# Keys
SETTINGS_KEY_EDITOR_COMMAND = "TextEditorCommand"
SETTINGS_KEY_DEFAULT_NOTE_STYLE = "DefaultNoteStyle" # Could store a JSON string of default style for new notes

# Initial default style values (can be overridden by user settings later)
INITIAL_STYLE = {
    "transparency": DEFAULT_NOTE_TRANSPARENCY,
    "backgroundColor": DEFAULT_NOTE_BG_COLOR,
    "margin": DEFAULT_NOTE_MARGIN
}

# Initial position for the very first note created if no others exist
INITIAL_POS_X = 100
INITIAL_POS_Y = 100

# Initial size for the very first note created
INITIAL_SIZE_W = DEFAULT_NOTE_WIDTH
INITIAL_SIZE_H = DEFAULT_NOTE_HEIGHT

if __name__ == '__main__':
    # For testing paths - not part of the app logic
    print(f"Config Dir: {CONFIG_DIR}")
    print(f"Data Dir: {DATA_DIR}")
    print(f"Settings File: {SETTINGS_FILE}")
    print(f"Database File: {DATABASE_FILE}")
