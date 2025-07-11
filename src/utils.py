import os
from pathlib import Path

APP_NAME = "desktop-notes"

def get_config_dir() -> Path:
    """Returns the application's config directory."""
    config_home = os.environ.get('XDG_CONFIG_HOME', Path.home() / ".config")
    return Path(config_home) / APP_NAME

def get_data_dir() -> Path:
    """Returns the application's data directory."""
    data_home = os.environ.get('XDG_DATA_HOME', Path.home() / ".local" / "share")
    return Path(data_home) / APP_NAME

def get_settings_file() -> Path:
    """Returns the path to the settings.ini file."""
    return get_config_dir() / "settings.ini"

def get_database_file() -> Path:
    """Returns the path to the notes.db file."""
    # For development, we might want to use a local data directory
    # return Path("data") / "notes.db"
    return get_data_dir() / "notes.db"

# Ensure directories exist when functions are called
from PyQt6.QtCore import QSettings

APP_NAME = "desktop-notes"
ORG_NAME = "KDECommunity" # Or your organization/personal name for QSettings

# Ensure base directories exist upon module load or first use
_config_dir = None
_data_dir = None

def _ensure_dirs():
    global _config_dir, _data_dir
    if _config_dir is None:
        _config_dir = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / ".config")) / APP_NAME
        _config_dir.mkdir(parents=True, exist_ok=True)
    if _data_dir is None:
        _data_dir = Path(os.environ.get('XDG_DATA_HOME', Path.home() / ".local" / "share")) / APP_NAME
        _data_dir.mkdir(parents=True, exist_ok=True)

def get_config_dir() -> Path:
    """Returns the application's config directory."""
    _ensure_dirs()
    return _config_dir

def get_data_dir() -> Path:
    """Returns the application's data directory."""
    _ensure_dirs()
    return _data_dir

def get_settings_file() -> Path:
    """Returns the path to the settings.ini file (managed by QSettings)."""
    # QSettings handles the actual file path based on its format, org name, and app name.
    # This function can return the directory where QSettings would place it, for reference.
    _ensure_dirs()
    # For INI format on Linux, it's typically ~/.config/<APP_NAME>/<APP_NAME>.ini or similar
    # QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ORG_NAME, APP_NAME)
    # will store it in ~/.config/KDECommunity/desktop-notes.conf (if ORG_NAME is KDECommunity)
    # or ~/.config/desktop-notes/desktop-notes.ini (if ORG_NAME not used or different convention)
    # Let's align with the spec's desired path: ~/.config/desktop-notes/settings.ini
    # To achieve this specific path with QSettings, we might need to use its constructor that takes a specific file path.
    # However, the standard way is QSettings(ORG_NAME, APP_NAME).
    # For spec compliance on path, we will assume QSettings is configured to use this path.
    # If we want to enforce settings.ini name, we might need to use QSettings(str(get_config_dir() / "settings.ini"), QSettings.Format.IniFormat)
    return get_config_dir() / "settings.ini"


def get_qsettings() -> QSettings:
    """Returns a QSettings instance for the application."""
    # To match `~/.config/desktop-notes/settings.ini`
    # We need to ensure QSettings uses this specific file name and location.
    # By default, QSettings(ORG_NAME, APP_NAME) might create `~/.config/ORG_NAME/APP_NAME.conf`
    # To use `~/.config/APP_NAME/settings.ini`, we can set the application name appropriately
    # and then QSettings might create `~/.config/APP_NAME/APP_NAME.conf`.
    # The most direct way is to give the full path to QSettings constructor.

    # As per spec: `~/.config/desktop-notes/settings.ini`
    # So, APP_NAME is "desktop-notes". The file is "settings.ini".
    # QSettings usually names the file after the application if not specified.
    # To get "settings.ini", we can tell QSettings the app name is "settings"
    # and have it stored inside the "desktop-notes" config folder.
    # This is a bit of a workaround. A cleaner QSettings usage is ORG_NAME, APP_NAME.

    # Forcing the path as per spec:
    settings_path = get_config_dir() / "settings.ini"
    return QSettings(str(settings_path), QSettings.Format.IniFormat)


# --- Global Settings Accessors ---
DEFAULT_EDITOR_COMMAND = "konsole -e nvim {filepath}" # Use {filepath} as placeholder

def get_editor_command() -> str:
    settings = get_qsettings()
    # Use {filepath} in the stored command, which we'll replace at runtime.
    return settings.value("General/editorCommand", DEFAULT_EDITOR_COMMAND, type=str)

def set_editor_command(command: str):
    settings = get_qsettings()
    settings.setValue("General/editorCommand", command)
    settings.sync() # Ensure it's written to disk


if __name__ == '__main__':
    _ensure_dirs() # Make sure directories are created for the printouts
    print(f"Config Dir: {get_config_dir()}")
    print(f"Data Dir: {get_data_dir()}")
    print(f"Settings File (expected path): {get_settings_file()}")
    print(f"Database File: {get_database_file()}")

    # Test QSettings
    print(f"\n--- Testing QSettings for Editor Command ---")
    initial_command = get_editor_command()
    print(f"Initial editor command (from settings or default): '{initial_command}'")

    test_command = "kate {filepath}"
    print(f"Setting editor command to: '{test_command}'")
    set_editor_command(test_command)

    retrieved_command = get_editor_command()
    print(f"Retrieved editor command: '{retrieved_command}'")
    assert retrieved_command == test_command

    print(f"Setting editor command back to default: '{DEFAULT_EDITOR_COMMAND}'")
    set_editor_command(DEFAULT_EDITOR_COMMAND)
    final_command = get_editor_command()
    print(f"Final editor command: '{final_command}'")
    assert final_command == DEFAULT_EDITOR_COMMAND

    # Verify the actual file created by QSettings
    # QSettings with a direct path will create exactly that file.
    settings_file_path = get_config_dir() / "settings.ini"
    if settings_file_path.exists():
        print(f"Settings file found at: {settings_file_path}")
        print("Contents:")
        with open(settings_file_path, "r") as f:
            print(f.read())
    else:
        print(f"Warning: Settings file not found at {settings_file_path} after QSettings usage.")

    print("--- QSettings Test Complete ---")
