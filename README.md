# Desktop Notes

Desktop Notes is a simple application for KDE Plasma 6 that allows users to display plain text (`.txt`) and Markdown (`.md`) files as read-only desktop widgets.

## Project Structure

```
desktop-notes/
├── src/
│   ├── main.py             # Main application logic / entry point for Plasma widget
│   ├── database.py         # SQLite database interaction (stores note configurations)
│   ├── note_widget.py      # Class for individual NoteWidget instances
│   ├── styling_dialog.py   # Dialog for note styling options
│   ├── management_view.py  # View for managing all notes (shown/hidden)
│   └── utils.py            # Utility functions (e.g., config paths)
├── data/                   # Stores notes.db during development (actual: ~/.local/share/desktop-notes/notes.db)
└── README.md               # This file
```

## Setup and Running

Currently under development.

### Database Initialization

The database schema is defined in `src/database.py`. It will be automatically created if it doesn't exist when the application first tries to access it. The default location for the database is `~/.local/share/desktop-notes/notes.db`.

To test database operations independently:
```bash
python -m src.database
```

This will create the database (if needed) in `~/.local/share/desktop-notes/notes.db` (or `./data/notes.db` if `get_database_file()` in `utils.py` is modified for local dev) and run some test operations.

### Main Application (Placeholder)

`src/main.py` is currently a placeholder. The actual integration as a KDE Plasma widget will require using KDE's development libraries and framework (e.g., Kirigami, KDeclarative, or PlasmaPy/Python bindings for PlasmA).

## Specifications

See `specs.md` for the detailed application requirements.
