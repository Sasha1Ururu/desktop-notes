import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from .utils import get_database_file

DATABASE_PATH = get_database_file()

def _init_db(db_path: Path = DATABASE_PATH) -> None:
    """Initializes the database and creates tables if they don't exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        status TEXT NOT NULL DEFAULT 'shown', -- "shown" or "hidden"
        filepath TEXT,                       -- Absolute path to the .txt or .md file
        position_x INTEGER NOT NULL DEFAULT 0,
        position_y INTEGER NOT NULL DEFAULT 0,
        width INTEGER NOT NULL DEFAULT 200,
        height INTEGER NOT NULL DEFAULT 150,
        transparency REAL NOT NULL DEFAULT 1.0, -- 0.0 (transparent) to 1.0 (opaque)
        backgroundColor TEXT NOT NULL DEFAULT '#FFFFE0', -- Light yellow default
        margin INTEGER NOT NULL DEFAULT 5        -- Uniform padding in pixels
    )
    """)
    conn.commit()
    conn.close()

# Initialize the database when this module is first imported
_init_db()

def _note_to_dict(row: Tuple) -> Optional[Dict[str, Any]]:
    """Converts a database row tuple to a dictionary."""
    if not row:
        return None
    columns = [
        "id", "status", "filepath",
        "position_x", "position_y", "width", "height",
        "transparency", "backgroundColor", "margin"
    ]
    data = dict(zip(columns, row))
    return {
        "id": data["id"],
        "status": data["status"],
        "filepath": data["filepath"],
        "position": {"x": data["position_x"], "y": data["position_y"]},
        "size": {"width": data["width"], "height": data["height"]},
        "style": {
            "transparency": data["transparency"],
            "backgroundColor": data["backgroundColor"],
            "margin": data["margin"]
        }
    }

def add_note(
    filepath: Optional[str] = None,
    status: str = "shown",
    position: Dict[str, int] = None,
    size: Dict[str, int] = None,
    style: Dict[str, Any] = None
) -> int:
    """Adds a new note to the database and returns its ID."""
    pos = position or {"x": 50, "y": 50} # Default position
    sz = size or {"width": 200, "height": 150} # Default size
    stl = style or {
        "transparency": 1.0,
        "backgroundColor": "#FFFFE0", # Light Yellow
        "margin": 5
    }

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO notes (status, filepath, position_x, position_y, width, height, transparency, backgroundColor, margin)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        status, filepath, pos.get("x", 50), pos.get("y", 50),
        sz.get("width", 200), sz.get("height", 150),
        stl.get("transparency", 1.0), stl.get("backgroundColor", "#FFFFE0"), stl.get("margin", 5)
    ))
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id

def get_note(note_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single note by its ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    conn.close()
    return _note_to_dict(row)

def get_all_notes() -> List[Dict[str, Any]]:
    """Retrieves all notes from the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [_note_to_dict(row) for row in rows if row]

def update_note(note_id: int, data: Dict[str, Any]) -> bool:
    """Updates an existing note.
    'data' can contain any of the 'note' structure fields.
    """
    fields = []
    values = []

    if "status" in data:
        fields.append("status = ?")
        values.append(data["status"])
    if "filepath" in data:
        fields.append("filepath = ?")
        values.append(data["filepath"])
    if "position" in data and isinstance(data["position"], dict):
        if "x" in data["position"]:
            fields.append("position_x = ?")
            values.append(data["position"]["x"])
        if "y" in data["position"]:
            fields.append("position_y = ?")
            values.append(data["position"]["y"])
    if "size" in data and isinstance(data["size"], dict):
        if "width" in data["size"]:
            fields.append("width = ?")
            values.append(data["size"]["width"])
        if "height" in data["size"]:
            fields.append("height = ?")
            values.append(data["size"]["height"])
    if "style" in data and isinstance(data["style"], dict):
        if "transparency" in data["style"]:
            fields.append("transparency = ?")
            values.append(data["style"]["transparency"])
        if "backgroundColor" in data["style"]:
            fields.append("backgroundColor = ?")
            values.append(data["style"]["backgroundColor"])
        if "margin" in data["style"]:
            fields.append("margin = ?")
            values.append(data["style"]["margin"])

    if not fields:
        return False # No valid fields to update

    values.append(note_id)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE notes SET {', '.join(fields)} WHERE id = ?", tuple(values))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error during update: {e}")
        return False
    finally:
        conn.close()

def delete_note(note_id: int) -> bool:
    """Deletes a note from the database by its ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()
    return deleted_count > 0

if __name__ == '__main__':
    # Test basic database operations
    print(f"Using database at: {DATABASE_PATH}")
    _init_db() # Ensure it's created

    # Clear existing notes for a clean test run
    all_notes_before_clear = get_all_notes()
    for note in all_notes_before_clear:
        delete_note(note['id'])
    print("Cleared existing notes for test.")

    print("Current notes:", get_all_notes())

    note1_id = add_note(filepath="/path/to/my/file.txt", position={"x": 10, "y": 20})
    print(f"Added note 1, ID: {note1_id}")

    note2_id = add_note(
        filepath="/another/doc.md",
        status="hidden",
        position={"x": 100, "y": 120},
        size={"width": 300, "height": 200},
        style={"transparency": 0.8, "backgroundColor": "#ABCDEF", "margin": 10}
    )
    print(f"Added note 2, ID: {note2_id}")

    print("All notes after adding:", get_all_notes())

    retrieved_note1 = get_note(note1_id)
    print("Retrieved note 1:", retrieved_note1)

    update_note(note1_id, {"status": "hidden", "style": {"backgroundColor": "#FF0000"}})
    print("Updated note 1 status and color")

    retrieved_note1_updated = get_note(note1_id)
    print("Retrieved note 1 after update:", retrieved_note1_updated)

    delete_note(note2_id)
    print(f"Deleted note 2 (ID: {note2_id})")

    print("All notes at the end:", get_all_notes())

    # Test adding a note with all defaults
    note3_id = add_note()
    print(f"Added note 3 with defaults, ID: {note3_id}")
    print("Retrieved note 3:", get_note(note3_id))
    print("All notes at the very end:", get_all_notes())
